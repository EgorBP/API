from typing import Final

from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Tag, UserGifTag
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
    
    async def fake_upsert_tags(
            self,
            tags: set[str]
    ) -> list[_model]:
        stmt = (
            insert(Tag)
            .values([{"tag": tag} for tag in tags])
            .on_conflict_do_update(
                index_elements=[Tag.tag],
                set_={"tag": Tag.tag},
            )
            .returning(self._model)
        )
        
        result = await self._session.scalars(stmt)
        return list(result)

    async def get_unique_user_tags(
            self,
            user_id: int,
    ) -> list[str]:
        stmt = (
            select(Tag.tag)
            .distinct()
            .select_from(UserGifTag)
            .join(Tag, UserGifTag.tag_id == Tag.id)
            .where(UserGifTag.user_id == user_id)
        )

        return list(await self._session.scalars(stmt))

    async def get_popular_tags(
            self,
            limit: int
    ) -> list[str]:
        stmt = (
            select(
                Tag.tag
            )
            .select_from(Tag)
            .join(UserGifTag, UserGifTag.tag_id == Tag.id)
            .group_by(Tag.tag)
            .order_by(
                func.count(UserGifTag.user_id).desc()
            )
            .limit(limit)
        )

        result = await self._session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_popular_gif_tags(
            self,
            gif_id: int,
            limit: int
    ) -> list[str]:
        stmt = (
            select(Tag.tag)
            .select_from(UserGifTag)
            .join(Tag, UserGifTag.tag_id == Tag.id)
            .where(UserGifTag.gif_id == gif_id)
            .group_by(Tag.tag)
            .order_by(func.count(UserGifTag.user_id).desc())
            .limit(limit)
        )
        
        tags = await self._session.scalars(stmt)
        return list(tags)
