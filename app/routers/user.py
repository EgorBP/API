from fastapi import APIRouter, Depends, HTTPException, Query
from app.schemas import GifOut, GifUpdate, Successful
from app.database import get_db
from app.services import get_user_gifs_with_tags, set_new_user_tags_on_gif, get_all_user_tags, delete_user_gif_tags


router = APIRouter(
    prefix='/user'
)


@router.get('/{tg_user_id}/gif/{tg_gif_id}', response_model=GifOut)
async def get_gif(
        tg_user_id: int,
        tg_gif_id: str,
        db=Depends(get_db)
):
    """
    Получить GIF пользователя по его Telegram ID и идентификатору GIF.

    - **tg_user_id**: Telegram ID пользователя
    - **tg_gif_id**: идентификатор GIF в Telegram

    **Returns:**
    Объект `GifOut` с полями:
    - **id**: int — внутренний ID GIF в базе
    - **tg_gif_id**: str — идентификатор GIF в Telegram
    - **tags**: list[str] — список тегов GIF
    """
    # Если что-то не найдено при попытке обращения выбросит ошибку
    try:
        data = (await get_user_gifs_with_tags(db, tg_user_id=tg_user_id, tg_gifs_id=tg_gif_id))['gifs_data'][0]
    except:
        raise HTTPException(status_code=404, detail="Data not found")

    return data


@router.put('/{tg_user_id}/gif/{tg_gif_id}', response_model=Successful)
async def update_gif_tags(
        tg_user_id: int,
        tg_gif_id: str,
        gif_data: GifUpdate,
        db=Depends(get_db)
):
    """
    Обновить список тегов для конкретного GIF пользователя.

    - **tg_user_id**: Telegram ID пользователя
    - **tg_gif_id**: идентификатор GIF в Telegram
    - **gif_data**: список новых тегов

    **Returns:**
    Объект `Successful`:
    - **successful**: bool — всегда `true`, если операция прошла успешно
    """
    await set_new_user_tags_on_gif(db, tg_user_id, tg_gif_id, gif_data.tags)
    # return get_user_gifs_with_tags(db, tg_id=tg_user_id, tg_gifs_id=tg_gif_id)['gifs_data'][0]
    return Successful()


@router.delete('/{tg_user_id}/gif/{gif_id}', response_model=Successful)
async def delete_gif_tags(
        tg_user_id: int,
        gif_id: str,
        gif_id_type: str | None = Query(None),
        db=Depends(get_db)
):
    """
    Удалить все связи тегов с конкретным GIF пользователя.

    - **tg_user_id**: Telegram ID пользователя
    - **gif_id**: идентификатор GIF (по умолчанию из telegram)
    - **gif_id_type**: выбор типа поиска для gif_id.
        - tg: поиск в базе по айди гифки из telegram
        - db: поиск в базе по айди гифки из внутренней БД

        Если не передано ничего выбирается вариант tg

    **Returns:**
    Объект `Successful`:
    - **successful**: bool — всегда `true`, если удаление прошло успешно
    """
    result = await delete_user_gif_tags(
        async_session=db,
        tg_user_id=tg_user_id,
        gif_id=gif_id,
        gif_id_type=gif_id_type,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Instances not found")

    return Successful()


@router.get('/{tg_user_id}/tags', response_model=list[str])
async def get_user_tags(
        tg_user_id: int,
        db=Depends(get_db)
):
    """
    Получение всех тегов пользователя по его Telegram ID.

    - **tg_user_id**: Telegram ID пользователя
    - **db**: подключение к базе данных через Depends

    **Возвращает**:
    Список тегов (list[str]) или HTTP 404, если пользователь не найден.
    """
    data = await get_all_user_tags(db, tg_user_id=tg_user_id)
    if not data:
        raise HTTPException(status_code=404, detail="User not found")

    return data
