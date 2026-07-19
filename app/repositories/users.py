from typing import Final

from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories import _BaseCRUD
from app.models import User


class UserRepository(_BaseCRUD):
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
        return await super().create_one({
            User.tg_id: tg_id
        })
