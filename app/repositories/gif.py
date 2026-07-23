from typing import Final, Sequence

from sqlalchemy import select, func, distinct, Row
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories import _BaseCRUD
from app.models import Gif, UserGifTag, Tag
from app.schemas.common import SortOption


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
        return await self.create_one({
            Gif.file_path: file_path,
            Gif.file_hash: file_hash
        })

    async def search_user_gifs_with_tags(
            self,
            user_id: int,
            gif_ids: Sequence[int] | None = None,
            tags: set[str] | None = None,
            cursor: int | None = None,
            limit: int | None = None
    ) -> list[Row[tuple]]:
        """
        Ищет GIF пользователя с возможностью фильтрации по тегам и идентификаторам.

        Метод возвращает только те GIF, которые принадлежат указанному пользователю.
        Если переданы теги, будут найдены только GIF, содержащие **все** указанные теги.

        :param user_id: Внутренний идентификатор пользователя. Если указан,
            поиск выполняется по нему. Должен быть передан либо `user_id`,
            либо `tg_user_id`.

        :param gif_ids: ID GIF или последовательность ID GIF,
            по которым необходимо ограничить поиск.

        :param tags: Тег или набор тегов для фильтрации. Возвращаются только GIF,
            содержащие все указанные теги.

        :return: Список найденных GIF.
        """

        stmt = (
            select(
                Gif.id,
                Gif.file_path,
                func.array_agg(Tag.tag).label("tags")
            )
            .select_from(UserGifTag)
            .join(Gif, UserGifTag.gif_id == Gif.id)
            .join(Tag, UserGifTag.tag_id == Tag.id)
            .order_by(Gif.id.desc())
            .where(UserGifTag.user_id == user_id)
            .group_by(
                Gif.id,
                Gif.file_path
            )
        )

        if gif_ids:
            stmt = stmt.where(Gif.id.in_(gif_ids))

        if tags:
            filter_query = (
                select(UserGifTag.gif_id)
                .select_from(UserGifTag)
                .join(Tag, UserGifTag.tag_id == Tag.id)
                .where(Tag.tag.in_(tags))
                .group_by(UserGifTag.gif_id)
                .having(func.count(distinct(Tag.tag)) == len(tags))
                .subquery()
            )

            stmt = stmt.join(filter_query, UserGifTag.gif_id == filter_query.c.gif_id)

        if cursor:
            stmt = stmt.where(Gif.id < cursor)

        if limit:
            stmt = stmt.limit(limit)

        result = await self._session.execute(stmt)
        return list(result.all())
    
    async def get_popular_gifs(
            self,
            limit: int
    ) -> list[Row[tuple[int, str]]]:
        stmt = (
            select(
                Gif.id,
                Gif.file_path,
            )
            .select_from(Gif)
            .outerjoin(UserGifTag, UserGifTag.gif_id == Gif.id)
            .group_by(Gif.id, Gif.file_path)
            .order_by(
                func.count(UserGifTag.user_id).desc(),
                Gif.id.desc()
            )
            .limit(limit)
        )
        
        result = await self._session.execute(stmt)
        return list(result.all())

    async def search_gifs_by_tags(
            self,
            tags: set[str] | None = None,
            sorting: SortOption = SortOption.NEW,
            cursor: int | None = None,
            limit: int | None = None
    ) -> list[Row[tuple[int, str]]]:
        stmt = (
            select(
                Gif.id,
                Gif.file_path,
            )
            .select_from(Gif)
            .outerjoin(UserGifTag, UserGifTag.gif_id == Gif.id)
        )
        
        if tags:
            stmt = (
                stmt.join(Tag, UserGifTag.tag_id == Tag.id)
                .where(Tag.tag.in_(tags))
            )

        if sorting == SortOption.NEW:
            stmt = stmt.order_by(Gif.id.desc())
        elif sorting == SortOption.POPULAR:
            stmt = (
                stmt.group_by(Gif.id)
                .order_by(func.count(UserGifTag.user_id).desc())
            )
        else:
            stmt = stmt.order_by(Gif.id.asc())

        if cursor:
            if sorting == SortOption.OLD:
                stmt = stmt.where(Gif.id > cursor)
            else:
                stmt = stmt.where(Gif.id < cursor)
            
        if limit:
            stmt = stmt.limit(limit)

        result = await self._session.execute(stmt)
        return list(result.all())

