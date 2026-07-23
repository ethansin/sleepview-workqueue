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
- Copy Client ID and Client Secret — these get stored in Secret Manager in §5,
  not pasted directly into the deploy command

Note: as long as the OAuth consent screen's "User Type" is Internal (restricted to the
westlakesleep.com Workspace) — or External with "Testing" status and the connected mailbox
added as a test user — requesting the sensitive `gmail.readonly` scope for the Gmail
integration below does **not** require Google's app verification review.

## 5. Create secrets in Secret Manager, then deploy backend to Cloud Run

**First-time setup only.** `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`,
`SESSION_SECRET`, and `GMAIL_POLL_SECRET` live in Secret Manager, not as
plain `--set-env-vars` values. This matters because `SESSION_SECRET` must be
generated **once** and reused for the lifetime of the service (every session
cookie is signed with it — regenerating it logs everyone out), and
`GMAIL_POLL_SECRET` must stay in sync with the Cloud Scheduler job in §9.
Keeping them in Secret Manager means a routine redeploy can never silently
regenerate or drop one of them — the only way any of these four values
change is a deliberate `gcloud secrets versions add`.

```bash
gcloud services enable secretmanager.googleapis.com

# One-time: create each secret with its value
printf '%s' 'YOUR_CLIENT_ID' | gcloud secrets create GOOGLE_CLIENT_ID --data-file=- --replication-policy=automatic
printf '%s' 'YOUR_CLIENT_SECRET' | gcloud secrets create GOOGLE_CLIENT_SECRET --data-file=- --replication-policy=automatic
openssl rand -hex 32 | tr -d '\n' | gcloud secrets create SESSION_SECRET --data-file=- --replication-policy=automatic
openssl rand -hex 32 | tr -d '\n' | gcloud secrets create GMAIL_POLL_SECRET --data-file=- --replication-policy=automatic

# Grant the Cloud Run runtime service account read access to each
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
RUNTIME_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

for s in GOOGLE_CLIENT_ID GOOGLE_CLIENT_SECRET SESSION_SECRET GMAIL_POLL_SECRET; do
  gcloud secrets add-iam-policy-binding "$s" \
    --member="serviceAccount:${RUNTIME_SA}" \
    --role="roles/secretmanager.secretAccessor"
done
```

`gcloud secrets versions access latest --secret=SESSION_SECRET` (or
`GMAIL_POLL_SECRET`) can always retrieve a value later — e.g. when syncing
the Cloud Scheduler header in §9 — so there's no need to separately save
these to a password manager.

`COOKIE_SECURE=true` is also required, not optional — the frontend
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
ALLOWED_DOMAINS=westlakesleep.com,\
FRONTEND_ORIGIN=https://YOUR_FIREBASE_HOSTING_URL,\
COOKIE_SECURE=true \
  --set-secrets GOOGLE_CLIENT_ID=GOOGLE_CLIENT_ID:latest,\
GOOGLE_CLIENT_SECRET=GOOGLE_CLIENT_SECRET:latest,\
SESSION_SECRET=SESSION_SECRET:latest,\
GMAIL_POLL_SECRET=GMAIL_POLL_SECRET:latest
```

### Updating an already-deployed service (e.g. adding/changing a config value)

Once the service is live, **never re-run the command above** — `--set-env-vars`
replaces the entire plain-env-var set, and `--set-secrets` replaces the entire
secret-ref set. Instead, use `--update-env-vars` for plain config values and
`--update-secrets` for secret-backed ones; both merge into the existing set
and leave everything else (including `COOKIE_SECURE` and the other secret
refs) untouched:

```bash
# Changing/adding a plain config value:
gcloud run deploy sleepview-backend \
  --source . \
  --region us-central1 \
  --update-env-vars FRONTEND_ORIGIN=https://YOUR_NEW_FIREBASE_URL
```

Rotating one of the four secret-backed values takes two steps. Cloud Run
resolves `:latest` **at deploy time**, not dynamically, so adding a new
secret version alone does nothing until a new revision is deployed:

```bash
# 1. Add the new secret version
echo -n "NEW_VALUE" | gcloud secrets versions add GMAIL_POLL_SECRET --data-file=-

# 2. Force a new revision so it picks up :latest
gcloud run services update sleepview-backend \
  --region us-central1 \
  --update-secrets=GMAIL_POLL_SECRET=GMAIL_POLL_SECRET:latest
```

If you rotate `GMAIL_POLL_SECRET` specifically, also update the Cloud
Scheduler job's header in the same operation — see §9. Cloud Scheduler
headers are static strings and can't read from Secret Manager directly, so
this one sync step can't be automated away.

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

There is no batch endpoint, so to seed several study IDs at once, use
`scripts/seed_study_ids.sh`, which loops the same request over a file of IDs
(one per line) and reports per-ID success/failure:

```bash
BASE_URL=https://YOUR_CLOUD_RUN_URL \
SESSION=ADMIN_SESSION_TOKEN \
./scripts/seed_study_ids.sh study_ids.txt
```

## 9. Cloud Scheduler — Gmail poll trigger
The backend polls Gmail via `POST /internal/gmail/poll`, gated by the
`GMAIL_POLL_SECRET` shared secret and by a configurable interval (default 30
minutes, editable from the admin UI without redeploying). Trigger it frequently
via Cloud Scheduler; the endpoint no-ops until the configured interval elapses.

The header value is read straight from Secret Manager rather than pasted in,
so it's always the value actually deployed in §5:

```bash
gcloud services enable cloudscheduler.googleapis.com

gcloud scheduler jobs create http gmail-poll-trigger \
  --location us-central1 \
  --schedule "*/5 * * * *" \
  --uri "https://YOUR_CLOUD_RUN_URL/internal/gmail/poll" \
  --http-method POST \
  --headers "X-Poll-Secret=$(gcloud secrets versions access latest --secret=GMAIL_POLL_SECRET)" \
  --attempt-deadline 60s
```

**If `GMAIL_POLL_SECRET` is ever rotated** (§5), this job's header goes stale
immediately and every poll attempt starts failing with `401
UNAUTHENTICATED` — Cloud Scheduler headers are static strings, so nothing
here updates automatically. Re-sync it as part of the same rotation:

```bash
gcloud scheduler jobs update http gmail-poll-trigger \
  --location us-central1 \
  --update-headers "X-Poll-Secret=$(gcloud secrets versions access latest --secret=GMAIL_POLL_SECRET)"
```

To check whether the job is actually succeeding (as opposed to just being
`ENABLED`, which only means it's scheduled to fire, not that it's
authenticating):

```bash
gcloud scheduler jobs describe gmail-poll-trigger --location us-central1 \
  --format="yaml(state,lastAttemptTime,status)"
```

An empty `status: {}` on the last attempt means success; a non-empty
`status.code` means it's failing — check
`gcloud logging read 'resource.type="cloud_scheduler_job" AND resource.labels.job_id="gmail-poll-trigger"' --freshness=1h`
for the underlying error.

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
- `SESSION_SECRET`, `GMAIL_POLL_SECRET`, `GOOGLE_CLIENT_ID`, and
  `GOOGLE_CLIENT_SECRET` live in Google Secret Manager (§5), not plain Cloud
  Run env vars reconstructed from memory each deploy — this removes the risk
  of accidentally rotating or dropping one of them as a side effect of an
  unrelated deploy (as happened once with both `SESSION_SECRET` and
  `COOKIE_SECURE`). `COOKIE_SECURE` itself is a non-sensitive plain env var
  and stays as `--update-env-vars`, not a secret.
- The one residual manual step: if `GMAIL_POLL_SECRET` is ever rotated, the
  Cloud Scheduler job's header must be re-synced in the same operation (§9)
  — Cloud Scheduler can't read Secret Manager values into HTTP headers
  itself
