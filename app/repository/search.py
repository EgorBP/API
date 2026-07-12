from typing import Sequence
from sqlalchemy import distinct
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models import User, UserGifTag, Gif, Tag
import logging

logger = logging.getLogger("app.repository")


class SearchRepository:
    """Общий класс для поиска"""
    def __init__(
            self,
            async_session: AsyncSession,
    ):
        """
        :param async_session: Объект асинхронной сессии SQLAlchemy.
        """
        self.async_session = async_session
        
    async def search_user_gifs_with_tags(
            self,
            user_id: int | None = None,
            tg_user_id: int | None = None,
            tg_gifs_id: Sequence[str] | str = None,
            tags: Sequence[str] | str = None,
    ):
        if user_id is None and tg_user_id is None:
            logger.error("Missing one of the required fields: user_id, tg_user_id")
            raise ValueError("Необходимо передать user_id или tg_user_id")

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
                UserGifTag.user_id,
                UserGifTag.gif_id,
                User.tg_id,
                Gif.tg_gif_id,
                func.array_agg(Tag.tag).label("tags")
            )
            .select_from(UserGifTag)
            .join(User, UserGifTag.user_id == User.id)
            .join(Gif, UserGifTag.gif_id == Gif.id)
            .join(Tag, UserGifTag.tag_id == Tag.id)
            .group_by(
                UserGifTag.user_id,
                UserGifTag.gif_id,
                User.tg_id,
                Gif.tg_gif_id
            )
        )
        
        if tg_gifs_id:
            stmt = stmt.where(Gif.tg_gif_id.in_(tg_gifs_id))
        if user_id is not None:
            stmt = stmt.where(UserGifTag.user_id == user_id)
        else:
            stmt = stmt.where(User.tg_id == tg_user_id)
        
        if tags:
            stmt = stmt.join(filter_query, UserGifTag.gif_id == filter_query.c.gif_id)

        result = await self.async_session.execute(stmt)
        return result.all()
