from sqlalchemy.orm import Session
from models import UserGifTag, User, Gif, Tag


def get_user_gifs_with_tags(
    session: Session,
    user_id: int | None = None,
    tg_id: int | None = None,
):
    """
    Возвращает список гифок пользователя с их тегами.

    Запрос связывает таблицы `users`, `gifs`, `tags` и `user_gif_tags`
    и возвращает для указанного пользователя все гифки с тегами.
    Фильтрация возможна либо по `user_id` (внутренний ID в базе),
    либо по `tg_id` (Telegram ID пользователя). Если указаны оба параметра,
    приоритет имеет `user_id`.

    :param session: объект сессии SQLAlchemy.
    :param user_id: внутренний ID пользователя (опционально).
    :param tg_id: Telegram ID пользователя (опционально).
    :return: список кортежей вида (tg_id, tg_gif_id, tag).
    """
    query = (
        session.query(UserGifTag.user_id, User.tg_id, Gif.tg_gif_id, Tag.tag)
        .join(User, UserGifTag.user_id == User.id)
        .join(Gif, UserGifTag.gif_id == Gif.id)
        .join(Tag, UserGifTag.tag_id == Tag.id)
    )

    if user_id:
        query = query.filter(UserGifTag.user_id == user_id)
    elif tg_id:
        query = query.filter(User.tg_id == tg_id)

    if not user_id:
        user_id = query.first().user_id

    result = {
        user_id: {
            'tg_id': query.first().tg_id,
            'gifs_data': {}
        }
    }

    for row in query.all():
        if row.tg_gif_id in result[user_id]['gifs_data']:
            result[user_id]['gifs_data'][row.tg_gif_id].append(row.tag)
        else:
            result[user_id]['gifs_data'][row.tg_gif_id] = [row.tag]

    return result


# def update_user_gifs_by_tags(session: Session, )
