from fastapi import APIRouter, Depends
from app.api.dependencies.auth import verify_secret_key
from app.api.v1.routers.bot.user import router as users_router

bot_router = APIRouter(
    prefix="/bot",
    dependencies = [Depends(verify_secret_key)]
)

bot_router.include_router(users_router, prefix="/users", tags=["Bot: Users"])
