from fastapi import APIRouter, Depends, Query, UploadFile, Form, status

from app.api.dependencies.auth import get_user_id_from_jwt
from app.api.dependencies.service import get_user_library_service, get_user_service
from app.api.dependencies.validation import validate_gif_file
from app.schemas.common import CursorPaginatedResponse
from app.schemas.gif import GifOut
from app.schemas.user import UserOut
from app.services import UserLibraryService
from app.services.user import UserService

router = APIRouter()


@router.get(
    '',
    response_model=UserOut
)
async def get_user_info(
        user_id: int = Depends(get_user_id_from_jwt),
        user_service: UserService = Depends(get_user_service)
):
    return await user_service.get_user_info(
        user_id=user_id
    )


@router.get(
    '/gifs/amount',
    response_model=int
)
async def get_user_gifs_amount(
        user_id: int = Depends(get_user_id_from_jwt),
        user_library_service: UserLibraryService = Depends(get_user_library_service)
):
    return await user_library_service.get_user_gifs_amount(
        user_id=user_id
    )

@router.get(
    '/gifs',
    response_model=CursorPaginatedResponse[GifOut, int]
)
async def get_user_gifs_by_id(
        gif_ids: list[int] | None = Query(None),
        tags: set[str] | None = Query(None),
        cursor: int | None = Query(None),
        limit: int = Query(default=20, ge=1, le=100),
        user_id: int = Depends(get_user_id_from_jwt),
        user_library_service: UserLibraryService = Depends(get_user_library_service)
):
    """
    Получить GIF пользователя по его Telegram ID и идентификатору GIF.

    - **user_id**: ID пользователя
    - **gif_id**: ID GIF

    **Returns:**
    Объект `GifOut` с полями:
    - **id**: int — внутренний ID GIF в базе
    - **tg_gif_id**: str — идентификатор GIF в Telegram
    - **tags**: list[str] — список тегов GIF
    """
    return await user_library_service.get_user_gifs_with_tags(
        user_id=user_id,
        gif_ids=gif_ids,
        tags=tags,
        cursor_id=cursor,
        limit=limit
    )


@router.get(
    '/tags/all', 
    response_model=list[str]
)
async def get_user_tags(
        user_id: int = Depends(get_user_id_from_jwt),
        user_library_service: UserLibraryService = Depends(get_user_library_service)
):
    """
    Получение всех тегов пользователя по его Telegram ID.

    - **user_id**: ID пользователя
    - **db**: Подключение к базе данных через Depends

    **Возвращает**:
    Список тегов (list[str]) или HTTP 404, если пользователь не найден.
    """
    return await user_library_service.get_all_user_tags(user_id=user_id)


@router.post(
    '/gifs/new',
    response_model=GifOut
)
async def upload_new_gif(
        file: UploadFile = Depends(validate_gif_file),
        tags: set[str] = Form(),
        user_id: int = Depends(get_user_id_from_jwt),
        user_library_service: UserLibraryService = Depends(get_user_library_service)
):
    return await user_library_service.add_new_user_gif(
        user_id=user_id,
        gif_file=file,
        tags=tags
    )


@router.put(
    '/gifs/{gif_id}/tags', 
    status_code=status.HTTP_204_NO_CONTENT
)
async def update_gif_tags(
        gif_id: int,
        tags: set[str],
        user_id: int = Depends(get_user_id_from_jwt),
        user_library_service: UserLibraryService = Depends(get_user_library_service)
):
    """
    Обновить список тегов для конкретного GIF пользователя.

    - **tg_user_id**: Telegram ID пользователя
    - **tg_gif_id**: идентификатор GIF в Telegram
    - **gif_data**: список новых тегов

    **Returns:** HTTP 204 если операция прошла успешно
    """
    await user_library_service.set_new_user_tags_on_gif(
        user_id=user_id,
        gif_id=gif_id,
        tags=tags
    )
    return


@router.delete(
    '/gifs', 
    response_model=int
)
async def delete_user_gif(
        gif_ids: list[int] = Query(),
        user_id: int = Depends(get_user_id_from_jwt),
        user_library_service: UserLibraryService = Depends(get_user_library_service)
):
    """
    Отвязывает GIF от пользователя, но не удаляет саму GIF из базы и хранилища.

    - **user_id**: ID пользователя
    - **gif_ids**: Идентификаторы GIF

    **Returns:** Количество удаленных GIF
    """
    return await user_library_service.unlink_user_from_gif(
        user_id=user_id,
        gif_ids=gif_ids
    )


@router.delete(
    '',
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_user(
        user_id: int = Depends(get_user_id_from_jwt),
        user_service: UserService = Depends(get_user_service)
):
    return await user_service.delete_user(
        user_id=user_id
    )
