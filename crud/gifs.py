from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from models import Gif
from utils import get_all_columns


def create_gif(session: Session, tg_gif_id: str):
    """
    Создаёт новую гифку в базе данных или возвращает существующую.

    Если в таблице `gifs` уже есть запись с таким `tg_gif_id`, новая не создаётся,
    и возвращается существующая. Если гифки ещё нет,
    она создаётся и возвращается.

    :param session: объект сессии SQLAlchemy.
    :param tg_gif_id: Telegram ID гифки.
    :return: объект с кортежем значений всех колонок модели Gif.
    """
    columns = get_all_columns(Gif)

    stmt = insert(Gif).values(tg_gif_id=tg_gif_id).on_conflict_do_nothing(
        index_elements=[Gif.tg_gif_id],
    ).returning(*columns)

    result = session.execute(stmt).fetchone()
    if not result:
        return session.query(*columns).filter(Gif.tg_gif_id == tg_gif_id).first()

    session.commit()
    return result