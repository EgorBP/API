from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Tag
from app.crud import _BaseCRUD


class TagsCRUD(_BaseCRUD):
    """
    CRUD для модели Tag.

    Переопределяется только логика создания записей.
    Остальные операции (get / update / delete) наследуются от BaseCRUD.
    """

    def __init__(self, async_session: AsyncSession):
        super().__init__(async_session, model=Tag)

    async def create_tag(
            self,
            tag: str,
    ):
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
        return await super().create_instance({
            Tag.tag: tag
        })
    