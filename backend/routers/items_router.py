"""Workqueue item endpoints for Role 1 (uploader) and Role 2 (reviewer)."""

from __future__ import annotations

import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from auth import get_current_user
from models.item import (
    CreateItemRequest,
    ItemStatus,
    Role1Data,
    Role2Data,
    SubmitRole1Request,
    SubmitRole2Request,
    WorkflowItem,
)
from services import firestore_service as db
from services import storage_service as storage

router = APIRouter(prefix="/items", tags=["items"])

DATE_FORMAT_PATTERN = re.compile(r"^\d{2}/\d{2}/\d{4}$")  # MM/DD/YYYY

ALLOWED_ROLES_UPLOAD = {"uploader", "admin"}
ALLOWED_ROLES_REVIEW = {"reviewer", "admin"}
ALLOWED_ROLES_CREATE = {"admin", "uploader"}  # admins can seed items; uploaders can too


# ── Admin / seed: create a new item in the queue ────────────────────────────

@router.post("", response_model=WorkflowItem, status_code=status.HTTP_201_CREATED)
async def create_item(body: CreateItemRequest, user: dict = Depends(get_current_user)):
    if user["role"] not in ALLOWED_ROLES_CREATE:
        raise HTTPException(status_code=403, detail="Not authorized.")
    return db.create_item(body.study_id, body.workflow_type, actor=user["sub"])


# ── Role 1: list pending-upload items ───────────────────────────────────────

@router.get("/upload-queue", response_model=list[WorkflowItem])
async def list_upload_queue(user: dict = Depends(get_current_user)):
    if user["role"] not in ALLOWED_ROLES_UPLOAD:
        raise HTTPException(status_code=403, detail="Not authorized.")
    return db.list_items_by_status(ItemStatus.pending_upload)


# ── Role 2: list pending-followup items ─────────────────────────────────────

@router.get("/followup-queue", response_model=list[WorkflowItem])
async def list_followup_queue(user: dict = Depends(get_current_user)):
    if user["role"] not in ALLOWED_ROLES_REVIEW:
        raise HTTPException(status_code=403, detail="Not authorized.")
    return db.list_items_by_status(ItemStatus.pending_followup)


# ── Get a single item ────────────────────────────────────────────────────────

@router.get("/{item_id}", response_model=WorkflowItem)
async def get_item(item_id: str, user: dict = Depends(get_current_user)):
    item = db.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found.")
    return item


# ── Role 1: submit report data + PDF ────────────────────────────────────────

@router.post("/{item_id}/submit-upload", response_model=WorkflowItem)
async def submit_upload(
    item_id: str,
    patient_last_name: str = Form(...),
    patient_first_name: str = Form(...),
    date_of_birth: str = Form(...),
    mrn: str = Form(...),
    medicare: bool = Form(default=False),
    clinical_note_expiration: str = Form(default=""),
    comments: str = Form(default=""),
    pdf: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    if user["role"] not in ALLOWED_ROLES_UPLOAD:
        raise HTTPException(status_code=403, detail="Not authorized.")

    item = db.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found.")
    if item.status != ItemStatus.pending_upload:
        raise HTTPException(status_code=400, detail="Item is not in pending_upload status.")

    if pdf.content_type not in ("application/pdf",):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    if not DATE_FORMAT_PATTERN.match(date_of_birth.strip()):
        raise HTTPException(status_code=400, detail="Date of birth must be in MM/DD/YYYY format.")

    if medicare:
        if not clinical_note_expiration.strip():
            raise HTTPException(
                status_code=400,
                detail="Clinical note expiration is required when Medicare is checked.",
            )
        if not DATE_FORMAT_PATTERN.match(clinical_note_expiration.strip()):
            raise HTTPException(
                status_code=400,
                detail="Clinical note expiration must be in MM/DD/YYYY format.",
            )

    pdf_bytes = await pdf.read()
    gcs_path = storage.upload_pdf(item_id, pdf_bytes)

    item.role1_data = Role1Data(
        patient_last_name=patient_last_name,
        patient_first_name=patient_first_name,
        date_of_birth=date_of_birth,
        mrn=mrn,
        medicare=medicare,
        clinical_note_expiration=(clinical_note_expiration.strip() or None) if medicare else None,
        comments=comments or None,
        pdf_gcs_path=gcs_path,
        completed_at=datetime.now(timezone.utc),
        completed_by=user["sub"],
    )
    item.status = ItemStatus.pending_followup
    return db.update_item(item, actor=user["sub"], action="submit_upload")


# ── Signed URL for PDF access ────────────────────────────────────────────────

@router.get("/{item_id}/pdf-url")
async def get_pdf_url(item_id: str, user: dict = Depends(get_current_user)):
    item = db.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found.")
    if not item.role1_data or not item.role1_data.pdf_gcs_path:
        raise HTTPException(status_code=404, detail="No PDF attached.")
    db.audit(user["sub"], "view_pdf", item_id)
    url = storage.generate_signed_url(item.role1_data.pdf_gcs_path)
    return {"url": url}


# ── Role 2: confirm follow-up ────────────────────────────────────────────────

@router.post("/{item_id}/confirm-followup", response_model=WorkflowItem)
async def confirm_followup(
    item_id: str, body: SubmitRole2Request, user: dict = Depends(get_current_user)
):
    if user["role"] not in ALLOWED_ROLES_REVIEW:
        raise HTTPException(status_code=403, detail="Not authorized.")

    item = db.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found.")
    if item.status != ItemStatus.pending_followup:
        raise HTTPException(status_code=400, detail="Item is not in pending_followup status.")

    if not body.followup_note.strip():
        raise HTTPException(status_code=400, detail="A follow-up note is required.")

    item.role2_data = Role2Data(
        followup_note=body.followup_note.strip(),
        confirmed_at=datetime.now(timezone.utc),
        confirmed_by=user["sub"],
    )
    item.status = ItemStatus.completed
    return db.update_item(item, actor=user["sub"], action="confirm_followup")
