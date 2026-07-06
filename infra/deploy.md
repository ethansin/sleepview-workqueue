# Deployment Guide

## Prerequisites
- GCP project with billing enabled
- Google Workspace domain (westlakesleep.com)
- `gcloud` CLI authenticated

## 1. Enable GCP APIs
```bash
gcloud services enable \
  run.googleapis.com \
  firestore.googleapis.com \
  storage.googleapis.com \
  cloudresourcemanager.googleapis.com
```

## 2. Firestore — create database
```bash
gcloud firestore databases create --location=us-central1
```

## 3. Cloud Storage — create bucket + apply lifecycle
```bash
PROJECT_ID=your-project-id
BUCKET=sleepview-reports-$PROJECT_ID

gcloud storage buckets create gs://$BUCKET \
  --location=US \
  --uniform-bucket-level-access

# Apply HIPAA retention lifecycle (6 years)
gcloud storage buckets update gs://$BUCKET \
  --lifecycle-file=infra/gcs-lifecycle.json

# Block all public access
gcloud storage buckets update gs://$BUCKET \
  --no-public-access-prevention=false
```

## 4. OAuth 2.0 credentials
- Go to GCP Console → APIs & Services → Credentials
- Create OAuth 2.0 Client ID (Web application)
- Authorized redirect URIs:
  - `https://YOUR_CLOUD_RUN_URL/auth/callback`
  - `https://YOUR_CLOUD_RUN_URL/admin/gmail/callback` (used by the Gmail integration, §10 below)
- Copy Client ID and Client Secret

Note: as long as the OAuth consent screen's "User Type" is Internal (restricted to the
westlakesleep.com Workspace) — or External with "Testing" status and the connected mailbox
added as a test user — requesting the sensitive `gmail.readonly` scope for the Gmail
integration below does **not** require Google's app verification review.

## 5. Build and deploy backend to Cloud Run

**First-time deploy only.** This command sets the full environment variable
set on the service. `SESSION_SECRET` must be generated **once** and reused for
the lifetime of the service — every session cookie is signed with it, so
re-running this exact command later (which evaluates `$(openssl rand -hex 32)`
fresh each time) mints a **new** `SESSION_SECRET` and immediately invalidates
every user's active login. Save the generated value somewhere durable (e.g. a
password manager) before moving on.

`COOKIE_SECURE=true` is also required here, not optional — the frontend
(Firebase Hosting) and backend (Cloud Run) are on different domains, so the
session cookie must be `SameSite=None; Secure` to survive cross-site
`fetch`/XHR calls from the SPA. `backend/routers/auth_router.py` only sets
`SameSite=None`/`Secure` when `COOKIE_SECURE=true`; leaving it out (it
defaults to `false`) silently breaks login for everyone, every time, since
the browser will never send the cookie back cross-site.

```bash
cd backend
gcloud run deploy sleepview-backend \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GCP_PROJECT_ID=$PROJECT_ID,\
GCS_BUCKET_NAME=$BUCKET,\
GOOGLE_CLIENT_ID=YOUR_CLIENT_ID,\
GOOGLE_CLIENT_SECRET=YOUR_CLIENT_SECRET,\
ALLOWED_DOMAINS=westlakesleep.com,\
SESSION_SECRET=$(openssl rand -hex 32),\
FRONTEND_ORIGIN=https://YOUR_FIREBASE_HOSTING_URL,\
COOKIE_SECURE=true,\
GMAIL_POLL_SECRET=$(openssl rand -hex 32)
```

### Updating an already-deployed service (e.g. adding a new env var)

Once the service is live, **never re-run the command above** — `--set-env-vars`
replaces the entire environment, so doing so regenerates `SESSION_SECRET` and
logs everyone out (and, as happened once already, can silently drop
`COOKIE_SECURE` and break login entirely if it's left out of the copy-pasted
command). Instead, use `--update-env-vars` with only the key(s) that are new
or changed; it merges into the existing environment and leaves everything
else (including `SESSION_SECRET` and `COOKIE_SECURE`) untouched:

```bash
gcloud run deploy sleepview-backend \
  --source . \
  --region us-central1 \
  --update-env-vars GMAIL_POLL_SECRET=$(openssl rand -hex 32)
```

## 6. Deploy frontend to Firebase Hosting
```bash
cd frontend
npm install -g firebase-tools
firebase login
firebase init hosting   # select your project, set public dir to "build"

REACT_APP_API_URL=https://YOUR_CLOUD_RUN_URL npm run build
firebase deploy --only hosting
```

## 7. Provision user roles in Firestore
Users must be manually added before they can log in.
Each document in the `users` collection uses the user's Google email as the document ID:

```
users/
  alice@westlakesleep.com → { role: "uploader" }
  bob@westlakesleep.com   → { role: "reviewer" }
  carol@westlakesleep.com → { role: "admin" }
```

Use the Firestore console or a one-time script to add these.

## 8. Seed study IDs into the queue
Study IDs are normally ingested automatically from the "SleepView HST report is
ready" notification emails via the Gmail integration (§9-10 below). As a
fallback/backfill for study IDs that arrive outside email, or that predate the
mailbox being connected, an admin can still create items manually via the API:

```bash
curl -X POST https://YOUR_CLOUD_RUN_URL/items \
  -H "Content-Type: application/json" \
  -H "Cookie: session=ADMIN_SESSION_TOKEN" \
  -d '{"study_id": "SLP-2024-00123"}'
```

## 9. Cloud Scheduler — Gmail poll trigger
The backend polls Gmail via `POST /internal/gmail/poll`, gated by the
`GMAIL_POLL_SECRET` shared secret and by a configurable interval (default 30
minutes, editable from the admin UI without redeploying). Trigger it frequently
via Cloud Scheduler; the endpoint no-ops until the configured interval elapses.

```bash
gcloud services enable cloudscheduler.googleapis.com

gcloud scheduler jobs create http gmail-poll-trigger \
  --location us-central1 \
  --schedule "*/5 * * * *" \
  --uri "https://YOUR_CLOUD_RUN_URL/internal/gmail/poll" \
  --http-method POST \
  --headers "X-Poll-Secret=YOUR_GMAIL_POLL_SECRET" \
  --attempt-deadline 60s
```

## 10. Connect the Gmail inbox
1. Sign into the shared notifications mailbox (e.g.
   `notifications@westlakesleep.com`) in a browser — an incognito window works
   well for this so it doesn't collide with your own Google session.
2. As an app admin, log into the SleepView Workqueue app and visit
   `/admin/gmail`.
3. Click "Connect Gmail" and complete the Google consent screen (granting
   read-only Gmail access).
4. Confirm the status shows "Connected as notifications@westlakesleep.com".
5. Use the "Check now" button to verify ingestion works before waiting for the
   next scheduled run.

## HIPAA Notes
- All data encrypted at rest (GCS + Firestore default AES-256)
- TLS enforced on Cloud Run (no HTTP)
- Session cookies: HttpOnly, Secure, SameSite=None (required since the
  frontend and backend are on different domains — see `COOKIE_SECURE` note
  in §5)
- PHI never written to Cloud Logging (audit log in Firestore only)
- PDF access logged in audit_log collection on every view
- GCS lifecycle deletes PDFs after 2190 days (6 years)
- Access scoped to @westlakesleep.com Google Workspace accounts only
- Gmail notification subjects/bodies are processed in-memory only and never
  written to Cloud Logging or the Firestore audit log — only extracted study
  IDs and per-run counts are persisted
- Consider signing a GCP BAA with Google before go-live
- Consider moving `SESSION_SECRET`/`GMAIL_POLL_SECRET`/`GOOGLE_CLIENT_SECRET`/
  `COOKIE_SECURE` into Google Secret Manager or a checked-in (private) env
  manifest instead of plain Cloud Run env vars reconstructed from memory each
  deploy — this removes the risk of accidentally rotating or dropping a
  setting (as happened once with both `SESSION_SECRET` and `COOKIE_SECURE`)
  as a side effect of an unrelated `--set-env-vars` deploy
