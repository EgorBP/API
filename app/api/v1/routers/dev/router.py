"""Combines the dev-facing routers under `/dev`."""

from fastapi import APIRouter

from app.api.v1.routers.dev.auth import router as auth_router

dev_router = APIRouter(
    prefix="/dev",
)

dev_router.include_router(auth_router, prefix="/auth", tags=["Dev: Auth"])
