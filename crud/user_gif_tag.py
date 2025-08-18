from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from models import UserGifTag
from utils import get_all_columns


def create_user_gif_tag(session: Session, user_id: int, gif_id: int, tag_id: int):
    """
    Создаёт новый тег в базе данных или возвращает существующий.

    Если в таблице `tags` уже есть запись с таким `tag`, новая не создаётся,
    и возвращается существующая. Если тега ещё нет,
    он создаётся и возвращается.

    :param session: объект сессии SQLAlchemy.
    :param tag: тег.
    :return: объект с кортежем значений всех колонок модели Gif.
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
