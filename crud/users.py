from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy import inspect
from models import User
from utils import is_valid_column_for_model


def crate_user(session: Session, tg_id: int):
    stmt = insert(User).values(tg_id=tg_id).on_conflict_do_nothing(
        index_elements=[User.tg_id],
    ).returning(User.id, User.tg_id, User.gif_count)

    result = session.execute(stmt).fetchone()
    session.commit()
    if result:
        return result.id, result.tg_id, result.gif_count

    return session.query(
        User.id, User.tg_id, User.gif_count
    ).filter(User.tg_id == tg_id).first()


def get_users(
        session: Session,
        columns: list[InstrumentedAttribute] | None=None,
        filters: dict[InstrumentedAttribute, list] | None=None
):
    """
    Получает пользователей с фильтрацией по колонкам.

    :param session: объект сессии SQLAlchemy.
    :param columns: колонки, которые нужно вернуть (например, User.tg_id).
    :param filters: словарь формата {column: value},
                    где column — объект колонки SQLAlchemy из таблицы User (например, User.tg_id),
                    value — список значений для фильтрации.
                    Можно передавать несколько колонок одновременно.
    :return: список колонок (id, tg_id, gif_count), соответствующих фильтрам.
    """

    if not columns:
        all_columns = [getattr(User, column.key) for column in User.__mapper__.columns]
        query = session.query(*all_columns)
    else:
        query = session.query(*columns)

    if not filters:
        return query.all()

    for column, values in filters.items():
        if is_valid_column_for_model(column, User) and isinstance(values, (list, tuple)):
            query = query.filter(column.in_(values))

    return query.all()


# def delete_user(session: Session, id: int):
