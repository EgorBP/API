from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories import _BaseCRUD
from app.models import UserGifTag
from sqlalchemy.orm.attributes import InstrumentedAttribute
from typing import Sequence
from sqlalchemy import select, Row
from typing import TypeAlias, Any
from app.models import User, Gif, Tag
from app.utils import get_orm_columns

JoinModel: TypeAlias = type[User | Gif | Tag]


class UserGifTagRepository(_BaseCRUD):
    """
    CRUD для модели UserGifTag.

    Переопределяется только логика создания связи.
    Остальные операции наследуются от BaseCRUD.    
    """

    def __init__(
            self, 
            session: AsyncSession
    ):
        super().__init__(session, model=UserGifTag)

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
        return await super().create_one({
            UserGifTag.user_id: user_id,
            UserGifTag.gif_id: gif_id,
            UserGifTag.tag_id: tag_id,
        })
    
    async def get_many_with_join(
            self,
            columns: Sequence[InstrumentedAttribute] | InstrumentedAttribute,
            join_models: Sequence[JoinModel] | JoinModel | None = None,
            filters: dict[InstrumentedAttribute, Sequence[Any] | Any] | None = None,
            scalars: bool = False
    ) ->  list[Row[tuple]] | list[Any]:
        """
        Метод получения записей из таблицы `UserGifTag` с фильтрацией по колонкам 
        и возможностью сделать inner join возможных таблиц.
        
        :param columns: Колонки для возврата. Если None — вернутся базовые колонки таблицы `UserGifTag`.
        :param join_models: Таблицы с которыми будет выполнен inner join. Если None — игнорируется.
        :param filters: Словарь {column: value}, где column — колонка модели (InstrumentedAttribute),
                       а value — значение для фильтрации.
        :param scalars: Будет ли применен scalars() к результату.
        :return: Список объектов с выбранными колонками.
        """
        if isinstance(columns, InstrumentedAttribute):
            columns = (columns,)
            
        if not columns:
            columns = get_orm_columns(self.model)

        stmt = select(*columns).select_from(UserGifTag)

        if join_models:
            if not isinstance(join_models, (list, tuple, set)):
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
                if not isinstance(values, (list, tuple, set)):
                    values = (values,)

                stmt = stmt.where(column.in_(values))
    
        result = await self.async_session.execute(stmt)
        if scalars:
            result = result.scalars()
        return result.all()
