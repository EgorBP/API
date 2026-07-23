from typing import Sequence
from sqlalchemy import distinct, Row
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models import User, UserGifTag, Gif, Tag
import logging

from app.schemas.common import SortOption

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
        self._session = session
        
    async def search_gifs_by_tags(
            self,
            tags: set[str] | None = None,
            sorting: SortOption = SortOption.NEW,
            cursor: int | None = None,
            limit: int | None = None
    ) -> list[Row[tuple]]:
        gif_id = 1
        popular_tags_query = (
            select(Tag.tag)
            .select_from(UserGifTag)
            .join(Tag, UserGifTag.tag_id == Tag.id)
            .where(UserGifTag.gif_id == gif_id)
            .group_by(Tag.tag)
            .order_by(func.count(UserGifTag.user_id).desc())
            .limit(5)
        )
        stmt = (
            select(
                Gif.id,
                Gif.file_path,
            )
            .select_from(UserGifTag)
            .join(Gif, UserGifTag.gif_id == Gif.id)
        )
        
        if sorting == sorting.NEW:
            stmt = stmt.order_by(Gif.id.desc())
        elif sorting == sorting.POPULAR:
            stmt = stmt.order_by(func.count(Gif.id).asc())
        else:
            stmt = stmt.order_by(Gif.id.asc())

        if cursor:
            stmt = stmt.where(Gif.id < cursor)

        if limit:
            stmt = stmt.limit(limit)

        result = await self._session.execute(stmt)
        return list(result.all())
