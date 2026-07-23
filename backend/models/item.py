from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class WorkflowType(str, Enum):
    sleep_report = "sleep_report"


class ItemStatus(str, Enum):
    pending_upload = "pending_upload"
    pending_followup = "pending_followup"
    completed = "completed"
    archived = "archived"


class Role1Data(BaseModel):
    patient_last_name: str
    patient_first_name: str
    date_of_birth: str  # MM/DD/YYYY, e.g. "01/15/1980"
    mrn: str
    medicare: bool = False
    clinical_note_expiration: Optional[str] = None  # MM/DD/YYYY; required if medicare
    comments: Optional[str] = None
    pdf_gcs_path: Optional[str] = None
    completed_at: Optional[datetime] = None
    completed_by: Optional[str] = None  # user email


class Role2Data(BaseModel):
    followup_note: str  # required confirmation note adds friction
    confirmed_at: Optional[datetime] = None
    confirmed_by: Optional[str] = None  # user email


class WorkflowItem(BaseModel):
    id: Optional[str] = None
    study_id: str
    workflow_type: WorkflowType = WorkflowType.sleep_report
    status: ItemStatus = ItemStatus.pending_upload
    role1_data: Optional[Role1Data] = None
    role2_data: Optional[Role2Data] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None


# ---- Request / Response shapes ----

class CreateItemRequest(BaseModel):
    study_id: str
    workflow_type: WorkflowType = WorkflowType.sleep_report


class SubmitRole1Request(BaseModel):
    patient_last_name: str
    patient_first_name: str
    date_of_birth: str
    mrn: str
    medicare: bool = False
    clinical_note_expiration: Optional[str] = None
    comments: Optional[str] = None


class SubmitRole2Request(BaseModel):
    followup_note: str


class ReactivateRequest(BaseModel):
    reason: str
