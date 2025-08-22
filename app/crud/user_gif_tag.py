from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from app.models import UserGifTag
from app.utils import get_all_columns


def create_user_gif_tag(session: Session, user_id: int, gif_id: int, tag_id: int):
    """
    Создаёт новую связь между пользователем, гифкой и тегом в таблице `user_gif_tags`
    или возвращает существующую.

    Если в таблице уже есть запись с таким `user_id`, `gif_id` и `tag_id`,
    новая не создаётся, и возвращается существующая.
    Если записи ещё нет, она создаётся и возвращается.  

    :param session: объект сессии SQLAlchemy.
    :param user_id: ID пользователя.
    :param gif_id: ID гифки.
    :param tag_id: ID тега.
    :return: объект с кортежем значений всех колонок модели UserGifTag.
    """
    columns = get_all_columns(UserGifTag)

    stmt = insert(UserGifTag).values(
        user_id=user_id,
        gif_id=gif_id,
        tag_id=tag_id
    ).on_conflict_do_nothing(
        index_elements=[*columns]
    ).returning(*columns)

    result = session.execute(stmt).fetchone()
    if not result:
        return session.query(*columns).filter(
            UserGifTag.user_id == user_id,
            UserGifTag.gif_id == gif_id,
            UserGifTag.tag_id == tag_id
        ).first()

    session.commit()
    return result
