from fastapi import APIRouter, Depends
from app.api.dependencies.auth import verify_secret_key
from app.api.routers.bot.users import router as users_router

bot_router = APIRouter(
    prefix="/bot",
    tags=["Telegram Bot"],
    dependencies = [Depends(verify_secret_key)]
)

bot_router.include_router(users_router, prefix="/users")
