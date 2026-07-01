from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from auth import get_current_user
from services.firestore_service import (
    approve_pending_user,
    list_pending_users,
    reject_pending_user,
)

router = APIRouter(prefix="/admin", tags=["admin"])


def _require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required.")
    return user


class ApproveRequest(BaseModel):
    role: str

    def validate_role(self) -> None:
        if self.role not in ("uploader", "reviewer", "admin"):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid role.")


@router.get("/pending-users")
async def get_pending_users(user: dict = Depends(_require_admin)):
    return list_pending_users()


@router.post("/approve-user/{email}", status_code=status.HTTP_200_OK)
async def approve_user(email: str, body: ApproveRequest, user: dict = Depends(_require_admin)):
    body.validate_role()
    approve_pending_user(email.lower(), body.role, actor=user["sub"])
    return {"message": f"User {email} approved with role {body.role}."}


@router.post("/reject-user/{email}", status_code=status.HTTP_200_OK)
async def reject_user(email: str, user: dict = Depends(_require_admin)):
    reject_pending_user(email.lower(), actor=user["sub"])
    return {"message": f"User {email} rejected."}
