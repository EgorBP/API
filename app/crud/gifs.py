from sqlalchemy.ext.asyncio import AsyncSession
from app.crud import _BaseCRUD
from app.models import Gif


class GifsCRUD(_BaseCRUD):
    """
    CRUD для модели Gif.
    
    Переопределяется только логика создания записей.
    Остальные операции наследуются от BaseCRUD.
    """
    
    def __init__(
            self, 
            async_session: AsyncSession
    ):
        super().__init__(async_session, model=Gif)

    async def create_gif(
            self,
            tg_gif_id: str,
    ):
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
        return await super().create_instance({
            Gif.tg_gif_id: tg_gif_id
        })
