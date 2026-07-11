from sqlalchemy.ext.asyncio import AsyncSession
from app.crud import _BaseCRUD
from app.models import UserGifTag
from sqlalchemy.orm.attributes import InstrumentedAttribute
from typing import Sequence
from sqlalchemy import select, Row
from typing import TypeAlias, Any
from app.models import User, Gif, Tag
from app.utils import get_orm_columns, is_valid_column_for_model

JoinModel: TypeAlias = type[User | Gif | Tag]


class UserGifTagCRUD(_BaseCRUD):
    """
    CRUD для модели UserGifTag.

    Переопределяется только логика создания связи.
    Остальные операции наследуются от BaseCRUD.    
    """

    def __init__(self, async_session: AsyncSession):
        super().__init__(async_session, model=UserGifTag)

    async def create_user_gif_tag(
            self,
            user_id: int,
            gif_id: int,
            tag_id: int,
    ):
        """
        Создаёт связь между пользователем, гифкой и тегом
        или возвращает существующую.

        При конфликте по уникальному ограничению
        (user_id, gif_id, tag_id) новая запись не создаётся,
        а возвращается существующая строка.

        :return: Row с колонками модели UserGifTag.
        """
        return await super().create_instance({
            UserGifTag.user_id: user_id,
            UserGifTag.gif_id: gif_id,
            UserGifTag.tag_id: tag_id,
        })
    
    async def get_instances_with_join(
            self,
            columns: Sequence[InstrumentedAttribute] | InstrumentedAttribute,
            join_models: Sequence[JoinModel] | JoinModel | None = None,
            filters: dict[InstrumentedAttribute, Sequence[Any] | Any] | None = None,
            scalar: bool = False
    ) ->  Sequence[Row[tuple]]:

        if not isinstance(columns, (list, tuple)):
            columns = (columns,)

        stmt = select(*columns).select_from(UserGifTag)

        if join_models:
            if not isinstance(join_models, (list, tuple)):
                join_models = (join_models,)

            for model in join_models:
                if model is User:
                    stmt = stmt.join(User, UserGifTag.user_id == User.id)
                elif model is Gif:
                    stmt = stmt.join(Gif, UserGifTag.gif_id == Gif.id)
                elif model is Tag:
                    stmt = stmt.join(Tag, UserGifTag.tag_id == Tag.id)

        if filters:
            for column, values in filters.items():
                if not isinstance(column, InstrumentedAttribute):
                    raise ValueError(f"В ключе для фильтрации ожидается колонка модели. "
                                     f"Вы передали {type(column)}, а именно {column}.")
                if not isinstance(values, (list, tuple)):
                    values = (values,)

                stmt = stmt.where(column.in_(values))
    
        result = await self.async_session.execute(stmt)
        if scalar:
            result = result.scalars()
        return result.all()
