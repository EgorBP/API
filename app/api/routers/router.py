from fastapi import APIRouter
from app.api.routers.web.router import web_router
from app.api.routers.bot.router import bot_router

api_router = APIRouter(
    prefix="/api/v1",
)

api_router.include_router(web_router)
api_router.include_router(bot_router)
