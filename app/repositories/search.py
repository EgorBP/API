from typing import Sequence
from sqlalchemy import distinct, Row
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models import User, UserGifTag, Gif, Tag
import logging

logger = logging.getLogger("app.repositories")


class SearchRepository:
    """Общий класс для поиска"""
    def __init__(
            self,
            session: AsyncSession,
    ):
        """
        :param session: Объект асинхронной сессии SQLAlchemy.
        """
        self.async_session = session
        
    async def search_user_gifs_with_tags(
            self,
            user_id: int | None = None,
            gif_ids: Sequence[int] | None = None,
            tags: set[str] | None = None,
            cursor_id: int | None = None,
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
        
        filter_query = (
            select(UserGifTag.gif_id)
            .select_from(UserGifTag)
            .join(Tag, UserGifTag.tag_id == Tag.id)
            .where(Tag.tag.in_(tags))
            .group_by(UserGifTag.gif_id)
            .having(func.count(distinct(Tag.tag)) == len(set(tags)))
            .subquery()
        )
        
        stmt = (
            select(
                UserGifTag.gif_id,
                Gif.file_path,
                func.array_agg(Tag.tag).label("tags")
            )
            .select_from(UserGifTag)
            .join(Gif, UserGifTag.gif_id == Gif.id)
            .join(Tag, UserGifTag.tag_id == Tag.id)
            .where(UserGifTag.user_id == user_id)
            .group_by(
                UserGifTag.gif_id,
                Gif.file_path
            )
        )
        
        if gif_ids:
            stmt = stmt.where(Gif.id.in_(gif_ids))
               
        if tags:
            stmt = stmt.join(filter_query, UserGifTag.gif_id == filter_query.c.gif_id)
        
        if cursor_id:
            stmt = stmt.order_by(UserGifTag.gif_id.desc())
            stmt = stmt.where(UserGifTag.gif_id < cursor_id)
        
        if limit:
            stmt = stmt.limit(limit)
        
        result = await self.async_session.execute(stmt)
        return result.all()
