from fastapi import APIRouter, Depends, HTTPException, Query, status, Form, UploadFile, File
from pydantic import ValidationError

from app.api.dependencies.services import get_user_library_service
from app.api.dependencies.validation import validate_gif_file
from app.schemas.common import UserGifsCursorPaginatedResponse
from app.schemas.gifs import GifUpdate, GifOut, GifCreate
from app.services import UserLibraryService

router = APIRouter()


@router.get(
    '/{tg_user_id}/gifs',
    response_model=UserGifsCursorPaginatedResponse
)
async def get_user_gifs(
        tg_user_id: int,
        gif_ids: list[int] | None = Query(None),
        tags: set[str] | None = Query(None),
        cursor: int | None = Query(None),
        limit: int = Query(default=20, ge=1, le=100),
        user_library_service: UserLibraryService = Depends(get_user_library_service)
):
    """
    Получить GIF пользователя по его Telegram ID и идентификатору GIF.

    - **tg_user_id**: Telegram ID пользователя
    - **gif_id**: ID GIF

    **Returns:**
    Объект `GifOut` с полями:
    - **id**: int — внутренний ID GIF в базе
    - **tg_gif_id**: str — идентификатор GIF в Telegram
    - **tags**: list[str] — список тегов GIF
    """
    return await user_library_service.get_user_gifs_with_tags(
        gif_ids=gif_ids,
        tags=tags,
        cursor_id=cursor,
        limit=limit
    )

@router.get(
    '/{tg_user_id}/tags/all',
    response_model=list[str]
)
async def get_user_tags(
        tg_user_id: int,
        user_library_service: UserLibraryService = Depends(get_user_library_service)
):
    """
    Получение всех тегов пользователя по его Telegram ID.

    - **tg_user_id**: Telegram ID пользователя
    - **db**: Подключение к базе данных через Depends

    **Возвращает**:
    Список тегов (list[str]) или HTTP 404, если пользователь не найден.
    """
    return await user_library_service.get_all_user_tags()


@router.post(
    '/{tg_user_id}/gifs/new',
    response_model=GifOut
)
async def upload_new_gif(
        tg_user_id: int,
        file: UploadFile = Depends(validate_gif_file),
        tags: set[str] = Form(),
        user_library_service: UserLibraryService = Depends(get_user_library_service)
):
    try:
        gif_create = GifCreate(tags=tags)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())
    
    return await user_library_service.add_new_user_gif(
        gif_file=file,
        gif_create=gif_create
    )


@router.put(
    '/{tg_user_id}/gifs/{gif_id}/tags',
    status_code=status.HTTP_204_NO_CONTENT
)
async def update_gif_tags(
        tg_user_id: int,
        gif_id: int,
        gif_data: GifUpdate,
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
        gif_id=gif_id,
        gif_update=gif_data
    )
    return


@router.delete(
    '/{tg_user_id}/gifs', 
    response_model=int
)
async def delete_user_gif(
        tg_user_id: int,
        gif_ids: list[int] = Query(),
        user_library_service: UserLibraryService = Depends(get_user_library_service)
):
    """
    Отвязывает GIF от пользователя, но не удаляет саму GIF из базы и хранилища.

    - **tg_user_id**: Telegram ID пользователя
    - **gif_ids**: Идентификаторы GIF

    **Returns:** Количество удаленных GIF
    """
    return await user_library_service.unlink_user_from_gif(
        gif_ids=gif_ids,
    )
