"""Google OAuth2 / Identity Platform authentication helpers.

Flow:
  - Frontend redirects user to /auth/login → we redirect to Google
  - Google redirects back to /auth/callback with a code
  - We exchange the code for tokens, verify the id_token, validate domain,
    look up (or create) the user's role in Firestore, then issue a signed
    session JWT that the frontend stores in an HttpOnly cookie.

Role assignment is managed in the `users` Firestore collection:
  users/{email} → { role: "uploader" | "reviewer" | "admin" }
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from fastapi import Cookie, HTTPException, Request, status
from jose import JWTError, jwt

from config import settings
from services.firestore_service import get_client

logger = logging.getLogger(__name__)

ALGORITHM = "HS256"
SESSION_TTL_HOURS = 10

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


def google_auth_redirect_url(redirect_uri: str) -> str:
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",
        "hd": settings.allowed_domains.split(",")[0],
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{GOOGLE_AUTH_URL}?{query}"


async def exchange_code(code: str, redirect_uri: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        resp.raise_for_status()
        return resp.json()


async def get_userinfo(access_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        resp.raise_for_status()
        return resp.json()


def _validate_domain(email: str) -> None:
    allowed = [d.strip() for d in settings.allowed_domains.split(",")]
    domain = email.split("@")[-1]
    if domain not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email domain not allowed.",
        )


def get_user_role(email: str) -> Optional[str]:
    db = get_client()
    doc = db.collection("users").document(email).get()
    if not doc.exists:
        return None
    return doc.to_dict().get("role")


def create_session_token(email: str, role: str, name: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=SESSION_TTL_HOURS)
    payload = {
        "sub": email,
        "role": role,
        "name": name,
        "exp": expire,
    }
    return jwt.encode(payload, settings.session_secret, algorithm=ALGORITHM)


def decode_session_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.session_secret, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session."
        )


async def get_current_user(session: Optional[str] = Cookie(default=None)) -> dict:
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")
    return decode_session_token(session)


def require_role(*roles: str):
    async def dependency(user: dict = None):
        from fastapi import Depends
        # This is resolved as a dependency chain; callers compose with get_current_user
        if user["role"] not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role.")
        return user

    return dependency
