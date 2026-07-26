"""Combines the web-facing users and auth routers under `/web`."""

from fastapi import APIRouter
from app.api.v1.routers.web.user import router as users_router
from app.api.v1.routers.web.auth import router as auth_router

web_router = APIRouter(
    prefix="/web",
)

web_router.include_router(users_router, prefix="/users/me", tags=["Web: Users"])
web_router.include_router(auth_router, prefix="/auth", tags=["Web: Auth"])
