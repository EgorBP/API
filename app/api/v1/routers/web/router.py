from fastapi import APIRouter
from app.api.v1.routers.web.user import router as users_router
from app.api.v1.routers.web.auth import router as auth_router
from app.api.v1.routers.web.gif import router as gifs_router
from app.api.v1.routers.web.tag import router as tags_router

web_router = APIRouter(
    prefix="/web",
)

web_router.include_router(users_router, prefix="/users/me", tags=["Web: Users"])
web_router.include_router(auth_router, prefix="/auth", tags=["Web: Auth"])
web_router.include_router(gifs_router, prefix="/gifs", tags=["Web: Gifs"])
web_router.include_router(tags_router, prefix="/tags", tags=["Web: Tags"])
