from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies.services import get_user_service
from app.schemas.common import UserGifsCursorPaginatedResponse
from app.schemas.gifs import GifUpdate
from app.services import UserService

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
        user_service: UserService = Depends(get_user_service)
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
    data = await user_service.get_user_gifs_with_tags(
        gif_ids=gif_ids,
        tags=tags,
        cursor_id=cursor,
        limit=limit
    )

    if not data:
        raise HTTPException(status_code=404, detail="Data not found")

    return data


@router.get(
    '/{tg_user_id}/tags/all',
    response_model=list[str]
)
async def get_user_tags(
        tg_user_id: int,
        user_service: UserService = Depends(get_user_service)
):
    """
    Получение всех тегов пользователя по его Telegram ID.

    - **tg_user_id**: Telegram ID пользователя
    - **db**: Подключение к базе данных через Depends

    **Возвращает**:
    Список тегов (list[str]) или HTTP 404, если пользователь не найден.
    """
    data = await user_service.get_all_user_tags()
    if not data:
        raise HTTPException(status_code=404, detail="User not found")

    return data


@router.put(
    '/{tg_user_id}/gif/{gif_id}/tags',
    status_code=status.HTTP_204_NO_CONTENT
)
async def update_gif_tags(
        tg_user_id: int,
        gif_id: int,
        gif_data: GifUpdate,
        user_service: UserService = Depends(get_user_service)
):
    """
    Обновить список тегов для конкретного GIF пользователя.

    - **tg_user_id**: Telegram ID пользователя
    - **tg_gif_id**: идентификатор GIF в Telegram
    - **gif_data**: список новых тегов

    **Returns:** HTTP 204 если операция прошла успешно
    """
    await user_service.set_new_user_tags_on_gif(
        tg_user_id=tg_user_id,
        gif_id=gif_id,
        tags=gif_data.tags
    )
    return


@router.delete('/{tg_user_id}/gif/{gif_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_gif_tags(
        tg_user_id: int,
        gif_id: int,
        gif_id_type: str | None = Query(None),
        user_service: UserService = Depends(get_user_service)
):
    """
    Удалить все связи тегов с конкретным GIF пользователя.

    - **tg_user_id**: Telegram ID пользователя
    - **gif_id**: идентификатор GIF (по умолчанию из telegram)
    - **gif_id_type**: выбор типа поиска для gif_id.
        - tg: поиск в базе по айди гифки из telegram
        - db: поиск в базе по айди гифки из внутренней БД

        Если не передано ничего выбирается вариант tg

    **Returns:** HTTP 204 если операция прошла успешно
    """
    result = await user_service.delete_user_gif_tags(
        tg_user_id=tg_user_id,
        gif_id=gif_id,
        gif_id_type=gif_id_type,
    )

    return
