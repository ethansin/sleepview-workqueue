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
        .stream()
    )
    items = [_deserialize(d) for d in docs]
    items.sort(key=lambda x: x.created_at or datetime.min)
    return items


def update_item(item: WorkflowItem, actor: str, action: str) -> WorkflowItem:
    db = get_client()
    item.updated_at = datetime.now(timezone.utc)
    db.collection(ITEMS_COLLECTION).document(item.id).set(_serialize(item))
    audit(actor, action, item.id)
    return item


def list_archived() -> list[WorkflowItem]:
    return list_items_by_status(ItemStatus.archived)


def study_id_exists(study_id: str) -> bool:
    db = get_client()
    docs = (
        db.collection(ITEMS_COLLECTION)
        .where("study_id", "==", study_id)
        .limit(1)
        .stream()
    )
    return len(list(docs)) > 0


APP_SETTINGS_COLLECTION = "app_settings"
GMAIL_SETTINGS_DOC = "gmail_integration"

_GMAIL_SETTINGS_DEFAULTS = {
    "connected": False,
    "connected_email": None,
    "connected_by": None,
    "connected_at": None,
    "refresh_token": None,
    "check_interval_minutes": 30,
    "lookback_days": 7,
    "last_checked_at": None,
    "last_run_status": None,
    "last_run_summary": None,
    "last_run_error": None,
}


def get_gmail_settings() -> dict:
    db = get_client()
    doc = db.collection(APP_SETTINGS_COLLECTION).document(GMAIL_SETTINGS_DOC).get()
    if not doc.exists:
        return dict(_GMAIL_SETTINGS_DEFAULTS)
    data = dict(_GMAIL_SETTINGS_DEFAULTS)
    data.update(doc.to_dict())
    return data


def update_gmail_settings(**fields) -> None:
    db = get_client()
    db.collection(APP_SETTINGS_COLLECTION).document(GMAIL_SETTINGS_DOC).set(
        fields, merge=True
    )


PENDING_USERS_COLLECTION = "pending_users"
FAILED_LOGIN_LIMIT = 10
LOCKOUT_MINUTES = 15


def create_pending_user(email: str, name: str, hashed_password: str) -> None:
    db = get_client()
    db.collection(PENDING_USERS_COLLECTION).document(email).set(
        {
            "email": email,
            "name": name,
            "hashed_password": hashed_password,
            "requested_at": datetime.now(timezone.utc),
            "status": "pending",
        }
    )


def get_pending_user(email: str) -> Optional[dict]:
    db = get_client()
    doc = db.collection(PENDING_USERS_COLLECTION).document(email).get()
    if not doc.exists:
        return None
    return doc.to_dict()


def list_pending_users() -> list[dict]:
    db = get_client()
    docs = (
        db.collection(PENDING_USERS_COLLECTION)
        .where("status", "==", "pending")
        .stream()
    )
    results = []
    for doc in docs:
        d = doc.to_dict()
        d.pop("hashed_password", None)
        results.append(d)
    results.sort(key=lambda x: x.get("requested_at") or datetime.min.replace(tzinfo=timezone.utc))
    return results


def approve_pending_user(email: str, role: str, actor: str) -> None:
    db = get_client()
    pending_doc = db.collection(PENDING_USERS_COLLECTION).document(email).get()
    if not pending_doc.exists:
        return
    data = pending_doc.to_dict()
    db.collection("users").document(email).set(
        {
            "role": role,
            "name": data.get("name", email),
            "hashed_password": data.get("hashed_password"),
            "failed_logins": 0,
        }
    )
    db.collection(PENDING_USERS_COLLECTION).document(email).delete()
    audit(actor, "approve_user", "", f"approved:{email} role:{role}")


def reject_pending_user(email: str, actor: str) -> None:
    db = get_client()
    db.collection(PENDING_USERS_COLLECTION).document(email).update({"status": "rejected"})
    audit(actor, "reject_user", "", f"rejected:{email}")


def increment_failed_login(email: str) -> None:
    from datetime import timedelta
    db = get_client()
    ref = db.collection("users").document(email)
    doc = ref.get()
    if not doc.exists:
        return
    data = doc.to_dict()
    count = (data.get("failed_logins") or 0) + 1
    update: dict = {"failed_logins": count}
    if count >= FAILED_LOGIN_LIMIT:
        update["locked_until"] = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MINUTES)
        update["failed_logins"] = 0
    ref.update(update)


def reset_failed_login(email: str) -> None:
    db = get_client()
    db.collection("users").document(email).update({"failed_logins": 0, "locked_until": None})
