from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.schemas.common import UserGifsCursorPaginatedResponse
from app.schemas.gifs import GifUpdate
from app.core.database import get_db
from app.services import UserService
from app.core.redis import get_redis

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
        db=Depends(get_db),
        redis=Depends(get_redis)
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
    user_service = UserService(db, redis)

    data = await user_service.get_user_gifs_with_tags(
        tg_user_id=tg_user_id,
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
        db=Depends(get_db),
        redis=Depends(get_redis)
):
    """
    Получение всех тегов пользователя по его Telegram ID.

    - **tg_user_id**: Telegram ID пользователя
    - **db**: Подключение к базе данных через Depends

    **Возвращает**:
    Список тегов (list[str]) или HTTP 404, если пользователь не найден.
    """
    user_service = UserService(db, redis)

    data = await user_service.get_all_user_tags(tg_user_id=tg_user_id)
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
        db=Depends(get_db),
        redis=Depends(get_redis)
):
    """
    Обновить список тегов для конкретного GIF пользователя.

    - **tg_user_id**: Telegram ID пользователя
    - **tg_gif_id**: идентификатор GIF в Telegram
    - **gif_data**: список новых тегов

    **Returns:** HTTP 204 если операция прошла успешно
    """
    user_service = UserService(db, redis)

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
        db=Depends(get_db),
        redis=Depends(get_redis)
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
    user_service = UserService(db, redis)

    result = await user_service.delete_user_gif_tags(
        tg_user_id=tg_user_id,
        gif_id=gif_id,
        gif_id_type=gif_id_type,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Instances not found")

    return
