from fastapi import APIRouter
from app.api.routers.web.users import router as users_router

web_router = APIRouter(
    prefix="/web",
    tags=["Web Client"]
)

web_router.include_router(users_router, prefix="/users")
