"""Polls a connected Gmail inbox for SleepView report-delivered notifications
and creates matching workqueue items.

Only emails matching the exact "SleepView HST report is ready" template AND
containing the word "delivered" are treated as valid triggers, since the same
inbox receives other similar-looking notifications (e.g. pending/processing)
that must not create queue items.
"""

from __future__ import annotations

import base64
import html as html_module
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from config import settings
from models.item import WorkflowType
from services import firestore_service as db

logger = logging.getLogger(__name__)

GMAIL_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
GMAIL_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GMAIL_TOKEN_URL = "https://oauth2.googleapis.com/token"

SEARCH_SUBJECT = "SleepView HST report is ready"

STUDY_ID_RE = re.compile(r"study\s*id\s*#?\s*(\d{10})\b", re.IGNORECASE)
DELIVERED_RE = re.compile(r"\bdelivered\b", re.IGNORECASE)
EXPECTED_SUBJECT = SEARCH_SUBJECT.lower()

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def gmail_auth_redirect_url(redirect_uri: str) -> str:
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": GMAIL_SCOPE,
        "access_type": "offline",
        "prompt": "consent",
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{GMAIL_AUTH_URL}?{query}"


def _normalize(text: str) -> str:
    text = html_module.unescape(text or "")
    text = _TAG_RE.sub(" ", text)
    text = _WS_RE.sub(" ", text).strip()
    return text


def extract_study_id(subject: str, body: str) -> Optional[str]:
    """Returns the 10-digit study ID if this email matches the delivered-report
    template, else None."""
    if EXPECTED_SUBJECT not in _normalize(subject).lower():
        return None

    norm_body = _normalize(body)
    if not DELIVERED_RE.search(norm_body):
        return None

    match = STUDY_ID_RE.search(norm_body)
    return match.group(1) if match else None


def _build_gmail_client(refresh_token: str, access_token: Optional[str] = None):
    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri=GMAIL_TOKEN_URL,
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        scopes=[GMAIL_SCOPE],
    )
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def get_connected_email(refresh_token: str, access_token: Optional[str] = None) -> str:
    """Returns the connected mailbox's address via the Gmail API itself, using
    only the already-granted gmail.readonly scope (not the separate OIDC
    userinfo endpoint, which would require an additional openid/email scope)."""
    client = _build_gmail_client(refresh_token, access_token)
    profile = client.users().getProfile(userId="me").execute()
    return profile.get("emailAddress", "")


def _list_candidate_messages(gmail_client, query: str) -> list[str]:
    ids: list[str] = []
    req = gmail_client.users().messages().list(userId="me", q=query, maxResults=100)
    while req is not None:
        resp = req.execute()
        ids.extend(m["id"] for m in resp.get("messages", []))
        req = gmail_client.users().messages().list_next(req, resp)
    return ids


def _decode_part_data(data: str) -> str:
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")


def _extract_plain_text(payload: dict) -> str:
    mime_type = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data")

    if mime_type == "text/plain" and body_data:
        return _decode_part_data(body_data)

    parts = payload.get("parts") or []
    if not parts:
        if mime_type == "text/html" and body_data:
            return _decode_part_data(body_data)
        return ""

    # Prefer a text/plain part; fall back to text/html; recurse into nested multiparts.
    html_fallback = ""
    for part in parts:
        part_mime = part.get("mimeType", "")
        part_data = part.get("body", {}).get("data")
        if part_mime == "text/plain" and part_data:
            return _decode_part_data(part_data)
        if part_mime == "text/html" and part_data and not html_fallback:
            html_fallback = _decode_part_data(part_data)
        elif part.get("parts"):
            nested = _extract_plain_text(part)
            if nested:
                return nested
    return html_fallback


def _get_message_text(gmail_client, message_id: str) -> tuple[str, str]:
    msg = (
        gmail_client.users()
        .messages()
        .get(userId="me", id=message_id, format="full")
        .execute()
    )
    payload = msg.get("payload", {})
    headers = {h["name"]: h["value"] for h in payload.get("headers", [])}
    subject = headers.get("Subject", "")
    body = _extract_plain_text(payload)
    return subject, body


def run_gmail_poll(actor: str = "system:gmail_poll") -> dict:
    """Executes one poll cycle. Returns a summary dict (no PHI/email content)."""
    gsettings = db.get_gmail_settings()
    if not gsettings.get("connected") or not gsettings.get("refresh_token"):
        db.update_gmail_settings(
            last_run_status="not_connected",
            last_checked_at=datetime.now(timezone.utc),
        )
        return {"status": "not_connected"}

    lookback_days = gsettings.get("lookback_days", 7)
    query = f'subject:"{SEARCH_SUBJECT}" newer_than:{lookback_days}d'

    created, skipped = 0, 0
    try:
        client = _build_gmail_client(gsettings["refresh_token"])
        for message_id in _list_candidate_messages(client, query):
            subject, body = _get_message_text(client, message_id)
            study_id = extract_study_id(subject, body)
            if not study_id:
                continue
            if db.study_id_exists(study_id):
                skipped += 1
                continue
            db.create_item(study_id, WorkflowType.sleep_report, actor=actor)
            created += 1

        db.update_gmail_settings(
            last_checked_at=datetime.now(timezone.utc),
            last_run_status="ok",
            last_run_summary=f"{created} new, {skipped} already queued",
            last_run_error=None,
        )
        return {"status": "ok", "created": created, "skipped": skipped}
    except Exception as e:
        logger.error("Gmail poll failed: %s", type(e).__name__)
        db.update_gmail_settings(
            last_checked_at=datetime.now(timezone.utc),
            last_run_status="error",
            last_run_error=type(e).__name__,
        )
        return {"status": "error"}


def is_due(gsettings: dict) -> bool:
    last_checked = gsettings.get("last_checked_at")
    interval = gsettings.get("check_interval_minutes", 30)
    if not last_checked:
        return True
    now = datetime.now(timezone.utc)
    return (now - last_checked) >= timedelta(minutes=interval)
