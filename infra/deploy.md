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
- Authorized redirect URIs: `https://YOUR_CLOUD_RUN_URL/auth/callback`
- Copy Client ID and Client Secret

## 5. Build and deploy backend to Cloud Run
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
FRONTEND_ORIGIN=https://YOUR_FIREBASE_HOSTING_URL
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
Study IDs arrive from your email notification system. For now, an admin user
can create items via the API:

```bash
curl -X POST https://YOUR_CLOUD_RUN_URL/items \
  -H "Content-Type: application/json" \
  -H "Cookie: session=ADMIN_SESSION_TOKEN" \
  -d '{"study_id": "SLP-2024-00123"}'
```

Future work: add a webhook endpoint that your notification email system can
POST to directly (e.g., via Gmail → Pub/Sub → Cloud Run).

## HIPAA Notes
- All data encrypted at rest (GCS + Firestore default AES-256)
- TLS enforced on Cloud Run (no HTTP)
- Session cookies: HttpOnly, Secure, SameSite=Lax
- PHI never written to Cloud Logging (audit log in Firestore only)
- PDF access logged in audit_log collection on every view
- GCS lifecycle deletes PDFs after 2190 days (6 years)
- Access scoped to @westlakesleep.com Google Workspace accounts only
- Consider signing a GCP BAA with Google before go-live
