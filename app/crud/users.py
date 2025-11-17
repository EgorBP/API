from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from app.models import User
from app.utils import get_orm_columns


async def create_user(session: Session, tg_id: int):
    """
    Создаёт нового пользователя в базе данных или возвращает существующего.

    Если в таблице `users` уже есть запись с таким `tg_id`, новая не создаётся,
    и возвращается существующий пользователь. Если пользователя ещё нет,
    он создаётся и возвращается.

    :param session: объект сессии SQLAlchemy.
    :param tg_id: Telegram ID пользователя.
    :return: объект с кортежем значений всех колонок модели User.
    """
    columns = get_orm_columns(User)

    # stmt = insert(User).values(tg_id=tg_id).on_conflict_do_nothing(
    #     index_elements=[User.tg_id],
    # ).returning(*columns)
    insert_stmt = insert(User).values(tg_id=tg_id)
    stmt = insert(User).values(tg_id=tg_id).on_conflict_do_update(
        index_elements=[User.tg_id],
        set_={'tg_id': insert_stmt.excluded.tg_id},
    ).returning(*columns)

    result = (await session.execute(stmt)).fetchone()
    # if not result:
    #     return session.query(*columns).filter(User.tg_id == tg_id).first()

    await session.commit()
    return result
