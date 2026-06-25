---
name: project-sleepview-workqueue
description: Core architecture and design decisions for the SleepView Workqueue app
metadata:
  type: project
---

SleepView Workqueue is a HIPAA-compliant web app for a sleep medicine office (Westlake Sleep, westlakesleep.com) that manages a two-stage report processing workflow.

**Why:** Non-tech-savvy office team needs a simple, readable workqueue for processing sleep study reports end-to-end — from PDF upload through external follow-up confirmation.

**Stack:**
- Backend: Python FastAPI on Cloud Run, Firestore (database), Cloud Storage (PDFs)
- Auth: Google OAuth2 with domain restriction to @westlakesleep.com; roles stored in Firestore `users/{email}` → `{role: "uploader"|"reviewer"|"admin"}`
- Frontend: React + TypeScript, Firebase Hosting
- Session: signed JWT in HttpOnly/Secure cookie (10hr TTL)

**Workflow statuses:** `pending_upload` → `pending_followup` → `completed` → `archived`

**Roles:**
- `uploader` (Role 1): sees upload queue, enters patient info (last name, first name, DOB, MRN, comments) + uploads PDF
- `reviewer` (Role 2): sees follow-up queue, views patient info + PDF, must write a follow-up note (friction by design) to confirm action taken
- `admin`: can access both queues, Record page, reactivate archived items

**Key files:**
- `backend/main.py` — FastAPI app entrypoint
- `backend/routers/items_router.py` — upload and followup queue endpoints
- `backend/routers/archive_router.py` — completed/archived record + reactivation
- `backend/routers/auth_router.py` — Google OAuth callback + session
- `backend/auth.py` — token creation/validation, role lookup
- `backend/services/firestore_service.py` — all Firestore operations + audit logging
- `backend/services/storage_service.py` — GCS upload + signed URLs
- `frontend/src/pages/UploadQueuePage.tsx` — Role 1 UI
- `frontend/src/pages/FollowupQueuePage.tsx` — Role 2 UI
- `frontend/src/pages/RecordPage.tsx` — archive/record browsing + admin reactivation
- `infra/deploy.md` — step-by-step GCP deployment instructions

**HIPAA posture:** Audit log in Firestore `audit_log` collection (never PHI in log messages); signed URLs for PDF access (15min expiry, every view audited); GCS lifecycle deletes PDFs after 2190 days (6 years); TLS enforced; session cookie HttpOnly+Secure.

**Modularity note:** `workflow_type` field on every item is the hook for future workflow types (e.g., patient intake). Do not implement additional workflow types until asked.

**How to apply:** When adding features or fixing bugs, maintain the status-machine flow (pending_upload → pending_followup → completed → archived) and always audit sensitive actions in Firestore rather than Cloud Logging.
