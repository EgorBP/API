"""Combines the web, bot, gifs, and tags routers under the `/v1` prefix."""

from fastapi import APIRouter
from app.api.v1.routers.web.router import web_router
from app.api.v1.routers.bot.router import bot_router
from app.api.v1.routers.gif import router as gifs_router
from app.api.v1.routers.tag import router as tags_router

v1_router = APIRouter(
    prefix="/v1",
)

v1_router.include_router(web_router)
v1_router.include_router(bot_router)
v1_router.include_router(gifs_router, prefix="/gifs", tags=["Web: Gifs"])
v1_router.include_router(tags_router, prefix="/tags", tags=["Web: Tags"])
