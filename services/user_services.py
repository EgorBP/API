from sqlalchemy.orm import Session
from models import UserGifTag, User, Gif, Tag
from crud import create_gif, create_tag, create_user, create_user_gif_tag, delete_instances, get_instances


def get_user_gifs_with_tags(
        session: Session,
        user_id: int | None = None,
        tg_id: int | None = None,
        tg_gifs_id: list[str] | str = None,
):
    """
    Возвращает гифки пользователя с тегами в виде вложенного словаря.

    Формирует структуру:
    {
        'user_id': Внутренний ID пользователя.

        'tg_id': Telegram ID пользователя,

        'gifs_data': {
            tg_gif_id: [список тегов],
            ...
        }
    }

    Таблицы `users`, `gifs`, `tags` и `user_gif_tags` связываются через JOIN.
    Фильтрация возможна по `user_id` (внутренний ID в базе) или `tg_id` (Telegram ID).
    Если указаны оба параметра, приоритет имеет `user_id`.

    :param session: объект сессии SQLAlchemy.
    :param user_id: внутренний ID пользователя (опционально).
    :param tg_id: Telegram ID пользователя (опционально).
    :param tg_gifs_id: Telegram ID гифок, которые нужно верунть, без него вернет все (опционально).
    :return: словарь с данными пользователя, гифок и тегов в формате,
        описанном выше или None если пользователь не найден.
    """
    if not user_id and not tg_id:
        return None

    if isinstance(tg_gifs_id, str):
        tg_gifs_id = (tg_gifs_id, )

    query = (
        session.query(UserGifTag.user_id, UserGifTag.gif_id, User.tg_id, Gif.tg_gif_id, Tag.tag)
        .join(User, UserGifTag.user_id == User.id)
        .join(Gif, UserGifTag.gif_id == Gif.id)
        .join(Tag, UserGifTag.tag_id == Tag.id)
    )

    if user_id:
        query = query.filter(UserGifTag.user_id == user_id)
    elif tg_id:
        query = query.filter(User.tg_id == tg_id)

    if not query.first():
        return None

    if not user_id:
        user_id = query.first().user_id

    result = {
        'user_id': user_id,
        'tg_id': query.first().tg_id,
        'gifs_data': []
    }

    gifs_data = []
    for row in query.all():
        # Если есть фильтр гифок, то проверяем вошла ли наша гифка в него если нет просто идем дальше
        if (tg_gifs_id and row.tg_gif_id in tg_gifs_id) or not tg_gifs_id:
            # Пытаемся получить индекс того словаря в котором есть гифка, если такого нету создаем новый
            try:
                index = [row.gif_id == data['gif_id'] for data in gifs_data].index(True)
            except ValueError:
                index = -1
            if index >= 0:
                gifs_data[index]['tags'].append(row.tag)
            else:
                gifs_data.append({
                    'gif_id': row.gif_id,
                    'tg_gif_id': row.tg_gif_id,
                    'tags': [row.tag]
                })

    result['gifs_data'] = gifs_data

    return result


def set_new_user_tags_on_gif(
        session: Session,
        tg_user_id,
        tg_gif_id: str,
        tags: list[str] | str,
):
    """
    Добавляет (или обновляет) связь между пользователем, гифкой и её тегами.

    Функция гарантирует, что:

    - если какого-либо поля не было в нужной таблице, оно автоматически создастся.
    - для каждой комбинации (user, gif, tag) создастся запись в таблице `user_gif_tags`.
    - старые теги будут удалены.

    :param session: объект сессии SQLAlchemy.
    :param tg_user_id: Telegram ID пользователя.
    :param tg_gif_id: Telegram ID гифки.
    :param tags: один тег или список тегов, которые будут связаны с гифкой.
    :return: None (изменения фиксируются в базе данных через session).
    """
    if isinstance(tags, str):
        tags = (tags, )

    old_data = get_user_gifs_with_tags(session, tg_id=tg_user_id, tg_gifs_id=tg_gif_id)

    # Удаляем старые ненужные теги
    if old_data['gifs_data']:
        for old_tag in old_data['gifs_data'][0]['tags']:
            if not old_tag in tags:
                tag_id = get_instances(session, Tag, Tag.id, {Tag.tag: old_tag})[0][0]
                delete_instances(session, UserGifTag, filters={
                    UserGifTag.user_id: old_data['user_id'],
                    UserGifTag.gif_id: old_data['gifs_data'][0]['gif_id'],
                    UserGifTag.tag_id: tag_id,
                })
            else:
                tags.remove(old_tag)

    user = create_user(session, tg_user_id)
    gif = create_gif(session, tg_gif_id)
    tags = [create_tag(session, tag) for tag in tags]

    for tag in tags:
        create_user_gif_tag(session, user_id=user.id, gif_id=gif.id, tag_id=tag.id)
