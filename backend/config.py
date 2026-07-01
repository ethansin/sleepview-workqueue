from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    gcp_project_id: str
    gcs_bucket_name: str
    google_client_id: str
    google_client_secret: str
    # Comma-separated allowed Google Workspace domain(s)
    allowed_domains: str = "westlakesleep.com"
    # Secret used to sign session tokens
    session_secret: str
    # CORS origin for the frontend
    frontend_origin: str = "http://localhost:3000"
    # Set to False for local HTTP development; True in production (HTTPS required)
    cookie_secure: bool = False
    # PDF retention days before archival deletion (HIPAA: 6 years minimum)
    retention_days: int = 2190  # 6 years

    class Config:
        env_file = ".env"


settings = Settings()
