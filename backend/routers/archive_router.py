"""Archive endpoints — completed items and reactivation."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from auth import get_current_user
from models.item import ItemStatus, ReactivateRequest
from services import firestore_service as db

router = APIRouter(prefix="/archive", tags=["archive"])

ALLOWED_ROLES = {"admin", "uploader", "reviewer"}


@router.get("")
async def list_archive(user: dict = Depends(get_current_user)):
    if user["role"] not in ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Not authorized.")
    items = db.list_archived()
    db.audit(user["sub"], "list_archive", "—")
    return items


@router.get("/completed")
async def list_completed(user: dict = Depends(get_current_user)):
    if user["role"] not in ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Not authorized.")
    return db.list_items_by_status(ItemStatus.completed)


@router.post("/{item_id}/archive")
async def archive_item(item_id: str, user: dict = Depends(get_current_user)):
    if user["role"] not in {"admin"}:
        raise HTTPException(status_code=403, detail="Only admins can manually archive.")
    item = db.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found.")
    if item.status != ItemStatus.completed:
        raise HTTPException(status_code=400, detail="Only completed items can be archived.")
    item.status = ItemStatus.archived
    item.archived_at = datetime.now(timezone.utc)
    return db.update_item(item, actor=user["sub"], action="archive_item")


@router.post("/{item_id}/reactivate")
async def reactivate_item(
    item_id: str, body: ReactivateRequest, user: dict = Depends(get_current_user)
):
    """Place an archived or completed item back into the appropriate queue."""
    if user["role"] not in {"admin"}:
        raise HTTPException(status_code=403, detail="Only admins can reactivate items.")

    item = db.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found.")
    if item.status not in (ItemStatus.archived, ItemStatus.completed):
        raise HTTPException(status_code=400, detail="Only archived/completed items can be reactivated.")

    if not body.reason.strip():
        raise HTTPException(status_code=400, detail="A reactivation reason is required.")

    # Determine which queue to return to based on how far along it was
    if item.role1_data and item.role1_data.pdf_gcs_path:
        item.status = ItemStatus.pending_followup
        action = "reactivate_to_followup"
    else:
        item.status = ItemStatus.pending_upload
        action = "reactivate_to_upload"

    item.archived_at = None
    return db.update_item(item, actor=user["sub"], action=action)
