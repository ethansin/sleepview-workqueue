"""Admin endpoints for connecting a Gmail inbox and configuring the poller."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

import auth
from config import settings
from services import firestore_service as db
from services import gmail_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/gmail", tags=["admin-gmail"])


def _require_admin(user: dict = Depends(auth.get_current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required.")
    return user


def _callback_uri(request: Request) -> str:
    return str(request.base_url).rstrip("/") + "/admin/gmail/callback"


class UpdateGmailSettingsRequest(BaseModel):
    check_interval_minutes: int
    lookback_days: int = 7

    def validate_ranges(self) -> None:
        if not (1 <= self.check_interval_minutes <= 1440):
            raise HTTPException(status_code=422, detail="check_interval_minutes must be between 1 and 1440.")
        if not (1 <= self.lookback_days <= 30):
            raise HTTPException(status_code=422, detail="lookback_days must be between 1 and 30.")


def _public_status(gsettings: dict) -> dict:
    return {
        "connected": gsettings.get("connected", False),
        "connected_email": gsettings.get("connected_email"),
        "connected_at": gsettings.get("connected_at"),
        "check_interval_minutes": gsettings.get("check_interval_minutes", 30),
        "lookback_days": gsettings.get("lookback_days", 7),
        "last_checked_at": gsettings.get("last_checked_at"),
        "last_run_status": gsettings.get("last_run_status"),
        "last_run_summary": gsettings.get("last_run_summary"),
        "last_run_error": gsettings.get("last_run_error"),
    }


@router.get("/status")
async def gmail_status(user: dict = Depends(_require_admin)):
    return _public_status(db.get_gmail_settings())


@router.get("/connect")
async def gmail_connect(request: Request, user: dict = Depends(_require_admin)):
    url = gmail_service.gmail_auth_redirect_url(_callback_uri(request))
    return RedirectResponse(url)


@router.get("/callback")
async def gmail_callback(code: str, request: Request, user: dict = Depends(_require_admin)):
    try:
        tokens = await auth.exchange_code(code, _callback_uri(request))
        refresh_token = tokens.get("refresh_token")
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google did not return a refresh token. Disconnect any prior grant for this "
                "account at https://myaccount.google.com/permissions and try connecting again.",
            )

        connected_email = gmail_service.get_connected_email(refresh_token, tokens.get("access_token"))

        db.update_gmail_settings(
            connected=True,
            connected_email=connected_email,
            connected_by=user["sub"],
            connected_at=datetime.now(timezone.utc),
            refresh_token=refresh_token,
        )
        db.audit(user["sub"], "gmail_connect", "", f"connected:{connected_email}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Gmail connect failed: %s", type(e).__name__)
        return RedirectResponse(url=f"{settings.frontend_origin}/admin/gmail?error=connect_failed")

    return RedirectResponse(url=f"{settings.frontend_origin}/admin/gmail")


@router.post("/disconnect")
async def gmail_disconnect(user: dict = Depends(_require_admin)):
    db.update_gmail_settings(
        connected=False,
        connected_email=None,
        connected_by=None,
        connected_at=None,
        refresh_token=None,
    )
    db.audit(user["sub"], "gmail_disconnect", "")
    return {"message": "Gmail inbox disconnected."}


@router.put("/settings")
async def update_settings(body: UpdateGmailSettingsRequest, user: dict = Depends(_require_admin)):
    body.validate_ranges()
    db.update_gmail_settings(
        check_interval_minutes=body.check_interval_minutes,
        lookback_days=body.lookback_days,
    )
    db.audit(
        user["sub"],
        "gmail_update_settings",
        "",
        f"interval={body.check_interval_minutes}m lookback={body.lookback_days}d",
    )
    return _public_status(db.get_gmail_settings())


@router.post("/check-now")
async def check_now(user: dict = Depends(_require_admin)):
    result = gmail_service.run_gmail_poll(actor=user["sub"])
    db.audit(user["sub"], "gmail_check_now", "", str(result.get("status")))
    return result
