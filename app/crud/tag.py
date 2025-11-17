from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from app.models import Tag
from app.utils import get_orm_columns


def create_tag(session: Session, tag: str):
    """
    Создаёт новый тег в базе данных или возвращает существующий.

    Если в таблице `tags` уже есть запись с таким `tag`, новая не создаётся,
    и возвращается существующая. Если тега ещё нет,
    он создаётся и возвращается.

    :param session: объект сессии SQLAlchemy.
    :param tag: тег.
    :return: объект с кортежем значений всех колонок модели Gif.
    """
    columns = get_orm_columns(Tag)

    stmt = insert(Tag).values(tag=tag).on_conflict_do_nothing(
        index_elements=[Tag.tag],
    ).returning(*columns)

    result = session.execute(stmt).fetchone()
    if not result:
        return session.query(*columns).filter(Tag.tag == tag).first()

    session.commit()
    return result