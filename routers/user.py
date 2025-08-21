from fastapi import APIRouter, Depends
from schemas import GifOut, GifUpdate, Successful
from database import get_db
from services import get_user_gifs_with_tags, set_new_user_tags_on_gif
from crud import delete_instances, get_instances
from models import UserGifTag, User, Gif


router = APIRouter(
    prefix='/user'
)


@router.get('/{tg_user_id}/gif/{tg_gif_id}', response_model=GifOut)
def get_gif(
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
    return get_user_gifs_with_tags(db, tg_id=tg_user_id, tg_gifs_id=tg_gif_id)['gifs_data'][0]


@router.put('/{tg_user_id}/gif/{tg_gif_id}', response_model=Successful)
def update_gif_tags(
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
    set_new_user_tags_on_gif(db, tg_user_id, tg_gif_id, gif_data.tags)
    # return get_user_gifs_with_tags(db, tg_id=tg_user_id, tg_gifs_id=tg_gif_id)['gifs_data'][0]
    return Successful()


@router.delete('/{tg_user_id}/gif/{gif_id}', response_model=Successful)
def delete_gif_tags(
        tg_user_id: int,
        tg_gif_id: str,
        db=Depends(get_db)
):
    """
    Удалить все связи тегов с конкретным GIF пользователя.

    - **tg_user_id**: Telegram ID пользователя
    - **tg_gif_id**: идентификатор GIF в Telegram

    **Returns:**
    Объект `Successful`:
    - **successful**: bool — всегда `true`, если удаление прошло успешно
    """
    delete_instances(db, UserGifTag, filters={
        UserGifTag.user_id: get_instances(db, User, columns=User.id, filters={User.tg_id: tg_user_id})[0][0],
        UserGifTag.gif_id: get_instances(db, Gif, columns=Gif.id, filters={Gif.tg_gif_id: tg_gif_id})[0][0],
    })
    return Successful()
