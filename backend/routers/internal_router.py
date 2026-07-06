"""Server-to-server endpoints authenticated by a shared secret, not a user
session. Used by Cloud Scheduler to trigger the Gmail poll gate."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, status

from config import settings
from services import firestore_service as db
from services import gmail_service

router = APIRouter(prefix="/internal", tags=["internal"])


def _require_poll_secret(x_poll_secret: str = Header(default=None)) -> None:
    if not settings.gmail_poll_secret or x_poll_secret != settings.gmail_poll_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid poll secret.")


@router.post("/gmail/poll", include_in_schema=False)
async def internal_gmail_poll(_: None = Depends(_require_poll_secret)):
    gsettings = db.get_gmail_settings()
    if not gmail_service.is_due(gsettings):
        return {"status": "skipped_not_due"}
    return gmail_service.run_gmail_poll(actor="system:gmail_poll")
