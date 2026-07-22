from fastapi import Depends, HTTPException, Request
from starlette import status
import logging

from app.api.dependencies.service import get_user_service
from app.services.user import UserService

logger = logging.getLogger("app.dependencies.users")


# TODO: update dockstring
async def get_or_create_user_id_by_tg_user_id(
        request: Request,
        user_service: UserService = Depends(get_user_service)
) -> int:
    tg_user_id_raw = request.path_params.get("tg_user_id")
    user_id_raw = request.path_params.get("user_id")
    
    if user_id_raw is not None:
        return int(user_id_raw)
    
    if tg_user_id_raw is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bad Request: authorization data was not transmitted."
        )
    
    tg_user_id = int(tg_user_id_raw)
    
    return await user_service.get_or_create_user_id_by_tg_user_id(tg_user_id)
