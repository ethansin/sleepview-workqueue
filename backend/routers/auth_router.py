from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse, RedirectResponse

import auth
from config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


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
        secure=True,
        samesite="lax",
        max_age=36000,  # 10 hours
    )
    return resp


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("session")
    return {"ok": True}


@router.get("/me")
async def me(user: dict = None):
    from fastapi import Depends
    from auth import get_current_user

    # re-expose as a proper dependency endpoint via the main app
    return user
