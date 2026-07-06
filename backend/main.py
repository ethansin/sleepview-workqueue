from __future__ import annotations

import logging

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from auth import get_current_user
from config import settings
from routers.admin_router import router as admin_router
from routers.archive_router import router as archive_router
from routers.auth_router import router as auth_router
from routers.gmail_router import router as gmail_router
from routers.internal_router import router as internal_router
from routers.items_router import router as items_router

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="SleepView Workqueue", version="1.0.0", docs_url="/api/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(items_router)
app.include_router(archive_router)
app.include_router(admin_router)
app.include_router(gmail_router)
app.include_router(internal_router)


@app.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return {"email": user["sub"], "role": user["role"], "name": user["name"]}


@app.get("/health")
async def health():
    return {"status": "ok"}
