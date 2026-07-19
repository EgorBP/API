from typing import Final
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories import _BaseCRUD
from app.models import Gif


# TODO: update dockstring
class GifRepository(_BaseCRUD[Gif]):
    """
    CRUD для модели Gif.
    
    Переопределяется только логика создания записей.
    Остальные операции наследуются от BaseCRUD.
    """
    _model: Final = Gif

    def __init__(
            self, 
            session: AsyncSession
    ):
        super().__init__(session)

    async def create_gif(
            self,
            file_path: str,
            file_hash: str
    ) -> _model:
        """
        Создаёт запись Gif в базе данных с указанным tg_gif_id.

        Этот метод является обёрткой над универсальным методом `create_instance`
        базового класса `_BaseCRUD`. Он обеспечивает:
            - строгую типизацию аргумента;
            - автоматическое создание словаря для вставки в таблицу `Gif`;
            - возврат первой найденной строки после вставки или при конфликте.

        В случае конфликта по уникальным или первичным ключам выполняется обновление
        первой найденной колонки таблицы на саму себя (поведение `ON CONFLICT DO UPDATE`),
        а возвращаемая строка содержит все колонки модели `Gif`.

        :param tg_gif_id: Строковый идентификатор GIF из Telegram, должен быть уникальным.
        :return: Row с колонками модели `Gif` после выполнения операции.
        """
        return await super().create_one({
            Gif.file_path: file_path,
            Gif.file_hash: file_hash
        })
