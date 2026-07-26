from fastapi import Depends, HTTPException, Request
from starlette import status
import logging

from app.api.dependencies.service import get_user_service
from app.services.user import UserService

logger = logging.getLogger("app.dependencies.users")


async def get_or_create_user_id_by_tg_user_id(
        request: Request,
        user_service: UserService = Depends(get_user_service)
) -> int:
    """FastAPI dependency resolving the target user ID from the path.

    Supports two route shapes: routes with a `{user_id}` path parameter
    (internal ID, used directly) and routes with a `{tg_user_id}` path
    parameter (Telegram ID, resolved — and the user created if this is
    their first request — via `UserService`). Exactly one of the two is
    expected to be present, with `user_id` taking priority if both are.

    Args:
        request: The current request, used to read path parameters.
        user_service: Service used to resolve/create the user when only
            `tg_user_id` is present.

    Returns:
        The internal user ID.

    Raises:
        HTTPException: 400, if neither `user_id` nor `tg_user_id` is
            present in the path.
    """
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
