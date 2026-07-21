from fastapi import APIRouter
from app.api.routers.web.users import router as users_router
from app.api.routers.web.auth import router as auth_router

web_router = APIRouter(
    prefix="/web",
    tags=["Web Client"]
)

web_router.include_router(users_router, prefix="/users/me")
web_router.include_router(auth_router, prefix="/auth", tags=["Auth"])
