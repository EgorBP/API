from typing import Final, Sequence, Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.repositories import _BaseCRUD
from app.models import User, UserGifTag, Gif
from app.repositories.base import T


# TODO
class UserRepository(_BaseCRUD[User]):
    """
    CRUD для модели User.

    Переопределяется только логика создания пользователя.
    Остальные операции наследуются от BaseCRUD.
    """
    _model: Final = User

    def __init__(
            self, 
            session: AsyncSession
    ):
        super().__init__(session)

    async def create_user(
            self,
            tg_id: int,
    ) -> _model:
        """
        Создаёт нового пользователя в базе данных или возвращает существующего.

        Метод является обёрткой над универсальным методом `create_instance`
        базового класса `_BaseCRUD`.

        Если в таблице `users` уже существует запись с таким `tg_id`
        (по уникальному ограничению), новая запись не создаётся,
        а возвращается существующая.

        В противном случае создаётся новый пользователь и возвращается
        строка со значениями всех колонок модели `User`.

        :param tg_id: Telegram ID пользователя.
        :return: Row с колонками модели `User` после вставки или при конфликте.
        """
        return await self.create_one({
            User.tg_id: tg_id
        })
    
    async def delete_user(
            self,
            user_id: int
    ) -> _model | None:
        user= await self.delete_many(
            filters={self._model.id: user_id}
        )
        
        return user[0] if user else None
    
    async def get_user_gifs_count(
            self,
            user_id: int
    ) -> int:
        stmt = (
            select(func.count(UserGifTag.gif_id))
            .select_from(UserGifTag)
            .where(UserGifTag.user_id == user_id)
        )
        
        return await self._session.scalar(stmt) or 0
