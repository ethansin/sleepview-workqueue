from __future__ import annotations

from pydantic import BaseModel, field_validator

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse, RedirectResponse

import auth
from config import settings
from services.firestore_service import (
    audit,
    create_pending_user,
    get_pending_user,
    get_client,
    increment_failed_login,
    reset_failed_login,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def email_valid(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Enter a valid email address.")
        return v

    @field_validator("password")
    @classmethod
    def password_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        return v


class PasswordLoginRequest(BaseModel):
    email: str
    password: str


def _callback_uri(request: Request) -> str:
    return str(request.base_url).rstrip("/") + "/auth/callback"


@router.get("/login")
async def login(request: Request):
    url = auth.google_auth_redirect_url(_callback_uri(request))
    return RedirectResponse(url)


@router.get("/callback")
async def callback(code: str, request: Request, response: Response):
    tokens = await auth.exchange_code(code, _callback_uri(request))
    userinfo = await auth.get_userinfo(tokens["access_token"])
    email = userinfo.get("email", "")
    name = userinfo.get("name", email)

    auth._validate_domain(email)

    role = auth.get_user_role(email)
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not provisioned. Contact an administrator.",
        )

    token = auth.create_session_token(email, role, name)
    resp = RedirectResponse(url=settings.frontend_origin)
    resp.set_cookie(
        key="session",
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="none" if settings.cookie_secure else "lax",
        max_age=36000,  # 10 hours
    )
    return resp


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(
        key="session",
        httponly=True,
        secure=settings.cookie_secure,
        samesite="none" if settings.cookie_secure else "lax",
    )
    return {"ok": True}


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest):
    email = body.email.lower()
    db = get_client()

    # Check not already a provisioned user
    if db.collection("users").document(email).get().exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists.")

    # Check not already pending
    existing_pending = get_pending_user(email)
    if existing_pending:
        if existing_pending.get("status") == "pending":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A request for this email is already pending approval.")
        # Rejected — allow re-application by overwriting

    hashed = auth.hash_password(body.password)
    create_pending_user(email, body.name.strip(), hashed)
    audit(email, "register_request", "", "")
    return {"message": "Account request submitted. An admin will review it shortly."}


@router.post("/login/password")
async def login_password(body: PasswordLoginRequest, response: Response):
    email = body.email.lower()
    db = get_client()

    user_doc = db.collection("users").document(email).get()
    if not user_doc.exists:
        # Return generic error to avoid account enumeration
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")

    user_data = user_doc.to_dict()

    if not user_data.get("hashed_password"):
        # Google OAuth account — no password set
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="This account uses Google sign-in.")

    auth.check_account_lockout(user_data)

    if not auth.verify_password(body.password, user_data["hashed_password"]):
        increment_failed_login(email)
        audit(email, "login_failed", "", "")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")

    reset_failed_login(email)
    role = user_data.get("role")
    name = user_data.get("name", email)
    token = auth.create_session_token(email, role, name)
    audit(email, "login_password", "", "")

    response.set_cookie(
        key="session",
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="none" if settings.cookie_secure else "lax",
        max_age=36000,
    )
    return {"email": email, "role": role, "name": name}


