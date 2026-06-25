from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from google.cloud import firestore

from config import settings
from models.item import ItemStatus, WorkflowItem

logger = logging.getLogger(__name__)

_client: Optional[firestore.Client] = None


def get_client() -> firestore.Client:
    global _client
    if _client is None:
        _client = firestore.Client(project=settings.gcp_project_id)
    return _client


ITEMS_COLLECTION = "workflow_items"
AUDIT_COLLECTION = "audit_log"


def _serialize(item: WorkflowItem) -> dict:
    data = item.model_dump(exclude_none=True)
    # Convert datetime objects to Firestore-compatible format
    for field in ("created_at", "updated_at", "archived_at"):
        if field in data and isinstance(data[field], datetime):
            data[field] = data[field]
    if "role1_data" in data:
        for f in ("completed_at",):
            if f in data["role1_data"] and isinstance(data["role1_data"][f], datetime):
                data["role1_data"][f] = data["role1_data"][f]
    if "role2_data" in data:
        for f in ("confirmed_at",):
            if f in data["role2_data"] and isinstance(data["role2_data"][f], datetime):
                data["role2_data"][f] = data["role2_data"][f]
    return data


def _deserialize(doc: firestore.DocumentSnapshot) -> WorkflowItem:
    data = doc.to_dict()
    data["id"] = doc.id
    # Firestore returns DatetimeWithNanoseconds; convert to plain datetime
    for field in ("created_at", "updated_at", "archived_at"):
        if field in data and data[field]:
            data[field] = datetime.fromisoformat(str(data[field]))
    return WorkflowItem(**data)


def audit(actor: str, action: str, item_id: str, detail: str = "") -> None:
    """Write a HIPAA audit log entry. Never include PHI in detail."""
    db = get_client()
    db.collection(AUDIT_COLLECTION).add(
        {
            "actor": actor,
            "action": action,
            "item_id": item_id,
            "detail": detail,
            "timestamp": datetime.now(timezone.utc),
        }
    )


def create_item(study_id: str, workflow_type: str, actor: str) -> WorkflowItem:
    db = get_client()
    now = datetime.now(timezone.utc)
    item = WorkflowItem(
        study_id=study_id,
        workflow_type=workflow_type,
        status=ItemStatus.pending_upload,
        created_at=now,
        updated_at=now,
    )
    _, ref = db.collection(ITEMS_COLLECTION).add(_serialize(item))
    item.id = ref.id
    audit(actor, "create_item", ref.id)
    return item


def get_item(item_id: str) -> Optional[WorkflowItem]:
    db = get_client()
    doc = db.collection(ITEMS_COLLECTION).document(item_id).get()
    if not doc.exists:
        return None
    return _deserialize(doc)


def list_items_by_status(status: ItemStatus) -> list[WorkflowItem]:
    db = get_client()
    docs = (
        db.collection(ITEMS_COLLECTION)
        .where("status", "==", status.value)
        .order_by("created_at")
        .stream()
    )
    return [_deserialize(d) for d in docs]


def update_item(item: WorkflowItem, actor: str, action: str) -> WorkflowItem:
    db = get_client()
    item.updated_at = datetime.now(timezone.utc)
    db.collection(ITEMS_COLLECTION).document(item.id).set(_serialize(item))
    audit(actor, action, item.id)
    return item


def list_archived() -> list[WorkflowItem]:
    return list_items_by_status(ItemStatus.archived)
