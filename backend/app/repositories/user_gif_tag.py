from collections.abc import Sequence
from typing import Any, Final, Literal, overload

from sqlalchemy import Row, delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import InstrumentedAttribute

from app.models import Gif, Tag, User, UserGifTag
from app.repositories import _BaseRepository
from app.utils import get_orm_columns

type JoinModel = type[User | Gif | Tag]


class UserGifTagRepository(_BaseRepository[UserGifTag]):
    """CRUD operations for the `UserGifTag` association model.

    Only `create_user_gif_tag` and read/delete helpers specific to this
    association are added here; generic get/update operations are
    inherited from `_BaseRepository`.
    """
    _model: Final = UserGifTag

    def __init__(
            self, 
            session: AsyncSession
    ):
        """Initializes the repository.

        Args:
            session: The async SQLAlchemy session to execute queries on.
        """
        super().__init__(session)

    async def create_user_gif_tag(
            self,
            user_id: int,
            gif_id: int,
            tag_id: int,
    ) -> _model:
        """Links a user, a GIF, and a tag.

        Thin wrapper around `create_one`. Does not check for an existing
        identical link first — callers that need idempotent creation are
        responsible for catching the conflict themselves.

        Args:
            user_id: Internal ID of the user.
            gif_id: Internal ID of the GIF.
            tag_id: Internal ID of the tag.

        Returns:
            The inserted `UserGifTag` row.

        Raises:
            IntegrityError: If this exact `(user_id, gif_id, tag_id)`
                combination already exists (unique constraint).
        """
        return await self.create_one({
            UserGifTag.user_id: user_id,
            UserGifTag.gif_id: gif_id,
            UserGifTag.tag_id: tag_id,
        })
    
    @overload
    async def get_many_with_join(
            self,
            columns: Sequence[InstrumentedAttribute] | InstrumentedAttribute,
            scalars: Literal[False] = False,
            join_models: Sequence[JoinModel] | JoinModel | None = None,
            filters: dict[InstrumentedAttribute, Sequence[Any] | Any] | None = None,
    ) ->  list[Row[tuple[Any]]]:
        ...
    
    @overload
    async def get_many_with_join(
            self,
            columns: Sequence[InstrumentedAttribute] | InstrumentedAttribute,
            scalars: Literal[True],
            join_models: Sequence[JoinModel] | JoinModel | None = None,
            filters: dict[InstrumentedAttribute, Sequence[Any] | Any] | None = None,
    ) ->  list[Any]:
        ...
    
    async def get_many_with_join(
            self,
            columns: Sequence[InstrumentedAttribute] | InstrumentedAttribute,
            scalars: bool = False,
            join_models: Sequence[JoinModel] | JoinModel | None = None,
            filters: dict[InstrumentedAttribute, Sequence[Any] | Any] | None = None,
    ) ->  list[Row[tuple[Any]]] | list[Any]:
        """Fetches `UserGifTag` rows, optionally joined with related tables.

        Unlike the generic `get_many`, this allows joining `User`, `Gif`,
        and/or `Tag` so both `columns` and `filters` can reference fields
        from those tables too (e.g. `Tag.tag`), not just from
        `UserGifTag` itself. Filter validation here only checks that a
        key is an `InstrumentedAttribute` — it does not require the
        column to belong to `UserGifTag` or to a model listed in
        `join_models`, so it is the caller's responsibility to only
        filter on columns that are actually joined into the statement.

        Args:
            columns: Column(s) to select, from `UserGifTag` or any model
                listed in `join_models`.
            scalars: If True, unwraps each result row to its single
                column value instead of returning a `Row`. Only makes
                sense when `columns` is a single column.
            join_models: Related model(s) to inner-join in, so their
                columns become selectable/filterable.
            filters: Mapping of column to value(s) to filter by. A value
                that is a list/tuple/set is matched with ``IN``; any
                other value is wrapped in a single-item tuple and also
                matched with ``IN``.

        Returns:
            A list of `Row` objects containing the requested columns, or
            a list of scalar values if `scalars` is True.

        Raises:
            ValueError: If a key in `filters` is not an
                `InstrumentedAttribute` at all.

        Example:
            Fetching the tag text for every tag a user has applied to a
            specific GIF::

                rows = await ugt_repo.get_many_with_join(
                    columns=Tag.tag,
                    join_models=Tag,
                    filters={UserGifTag.user_id: 1, UserGifTag.gif_id: 2},
                    scalars=True,
                )
        """
        if isinstance(columns, InstrumentedAttribute):
            columns = (columns,)
            
        if not columns:
            columns = get_orm_columns(self._model)

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
                    raise ValueError(f"Expected a model column as a filter key. "
                                     f"Got {type(column)}: {column}.")
                if not isinstance(values, (list, tuple, set)):
                    values = (values,)

                stmt = stmt.where(column.in_(values))
    
        result = await self._session.execute(stmt)
        if scalars:
            result = result.scalars()
        return list(result.all())

    async def delete_except_tag_ids(
            self,
            user_id: int,
            gif_id: int,
            keep_tag_ids: set[int],
    ) -> None:
        """Removes a user's tags from a GIF, keeping only the given ones.

        Used when replacing a GIF's tag set: rather than deleting
        everything and re-inserting, this deletes only the links whose
        tag is not in `keep_tag_ids`, leaving links to tags that should
        remain untouched.

        Args:
            user_id: Internal ID of the user.
            gif_id: Internal ID of the GIF.
            keep_tag_ids: Tag IDs that should NOT be deleted.
        """
        stmt = delete(self._model).where(
            UserGifTag.user_id == user_id,
            UserGifTag.gif_id == gif_id,
            UserGifTag.tag_id.not_in(keep_tag_ids),
        )
        await self._session.execute(stmt)
