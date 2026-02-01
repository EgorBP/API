from sqlalchemy.ext.asyncio import AsyncSession
from app.crud import _BaseCRUD
from app.models import User


class UsersCRUD(_BaseCRUD):
    """
    CRUD для модели User.

    Переопределяется только логика создания пользователя.
    Остальные операции наследуются от BaseCRUD.
    """

    def __init__(self, async_session: AsyncSession):
        super().__init__(async_session, model=User)

    async def create_user(
            self,
            tg_id: int,
    ):
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
        return await super().create_instance({
            User.tg_id: tg_id
        })
