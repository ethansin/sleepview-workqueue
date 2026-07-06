import os

# Required Settings fields must be present before `config` is imported by any
# module under test. Set test defaults here so tests don't need a real .env.
os.environ.setdefault("GCP_PROJECT_ID", "test-project")
os.environ.setdefault("GCS_BUCKET_NAME", "test-bucket")
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-client-id")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test-client-secret")
os.environ.setdefault("SESSION_SECRET", "test-session-secret")
os.environ.setdefault("GMAIL_POLL_SECRET", "test-poll-secret")
