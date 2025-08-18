from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from models import User
from utils import get_all_columns


def create_user(session: Session, tg_id: int):
    """
    Создаёт нового пользователя в базе данных или возвращает существующего.

    Если в таблице `users` уже есть запись с таким `tg_id`, новая не создаётся,
    и возвращается существующий пользователь. Если пользователя ещё нет,
    он создаётся и возвращается.

    :param session: объект сессии SQLAlchemy.
    :param tg_id: Telegram ID пользователя.
    :return: объект с кортежем значений всех колонок модели User.
    """
    columns = get_all_columns(User)

    stmt = insert(User).values(tg_id=tg_id).on_conflict_do_nothing(
        index_elements=[User.tg_id],
    ).returning(*columns)

    result = session.execute(stmt).fetchone()
    if not result:
        return session.query(*columns).filter(User.tg_id == tg_id).first()

    session.commit()
    return result
