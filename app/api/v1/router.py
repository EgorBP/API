from fastapi import APIRouter
from app.api.v1.routers.web.router import web_router
from app.api.v1.routers.bot.router import bot_router


v1_router = APIRouter(
    prefix="/v1",
)

v1_router.include_router(web_router)
v1_router.include_router(bot_router)
