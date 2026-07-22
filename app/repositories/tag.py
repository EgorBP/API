from typing import Final
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Tag
from app.repositories import _BaseCRUD


class TagRepository(_BaseCRUD[Tag]):
    """
    CRUD для модели Tag.

    Переопределяется только логика создания записей.
    Остальные операции (get / update / delete) наследуются от BaseCRUD.
    """
    _model: Final = Tag

    def __init__(
            self, 
            session: AsyncSession
    ):
        super().__init__(session)

    async def create_tag(
            self,
            tag: str,
    ) -> _model:
        """
        Создаёт новый тег в базе данных или возвращает существующий.

        Метод является обёрткой над универсальным методом `create_instance`
        базового класса `_BaseCRUD`.

        Если в таблице `tags` уже существует запись с таким значением `tag`
        (по уникальному ограничению или первичному ключу), новая запись
        не создаётся, а возвращается существующая.

        В случае отсутствия конфликта создаётся новая запись и возвращается
        строка со значениями всех колонок модели `Tag`.

        :param tag: Строковое значение тега (должно быть уникальным).
        :return: Row с колонками модели `Tag` после вставки или при конфликте.
        """
        return await self.create_one({
            Tag.tag: tag
        })
