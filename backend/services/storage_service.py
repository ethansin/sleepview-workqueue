from __future__ import annotations

import logging
from datetime import timedelta, timezone, datetime

import google.auth
import google.auth.transport.requests
from google.cloud import storage

from config import settings

logger = logging.getLogger(__name__)

_client: storage.Client | None = None


def get_client() -> storage.Client:
    global _client
    if _client is None:
        _client = storage.Client(project=settings.gcp_project_id)
    return _client


def upload_pdf(item_id: str, file_bytes: bytes, content_type: str = "application/pdf") -> str:
    """Upload a PDF and return the GCS path (not a public URL)."""
    client = get_client()
    bucket = client.bucket(settings.gcs_bucket_name)
    blob_name = f"reports/{item_id}/report.pdf"
    blob = bucket.blob(blob_name)
    blob.upload_from_string(file_bytes, content_type=content_type)
    return blob_name


def generate_signed_url(gcs_path: str, expiration_minutes: int = 15) -> str:
    """Return a short-lived signed URL for secure PDF access."""
    credentials, _ = google.auth.default()
    credentials.refresh(google.auth.transport.requests.Request())

    client = get_client()
    bucket = client.bucket(settings.gcs_bucket_name)
    blob = bucket.blob(gcs_path)
    url = blob.generate_signed_url(
        expiration=timedelta(minutes=expiration_minutes),
        method="GET",
        version="v4",
        service_account_email=credentials.service_account_email,
        access_token=credentials.token,
    )
    return url


def delete_pdf(gcs_path: str) -> None:
    client = get_client()
    bucket = client.bucket(settings.gcs_bucket_name)
    blob = bucket.blob(gcs_path)
    blob.delete()
