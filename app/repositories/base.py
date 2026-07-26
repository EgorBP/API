"""Generic async repository base class shared by all model-specific repositories.

Every repository in `app.repositories` (`UserRepository`, `GifRepository`,
`TagRepository`, `UserGifTagRepository`) subclasses `_BaseRepository` from
here rather than writing its own CRUD boilerplate. Model-specific
repositories only add operations that don't fit the generic filter-based
shape (e.g. `GifRepository.search_gifs_by_tags`).
"""

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, Row, Select, Update, Delete, Insert
from app.utils import is_valid_column_for_model, get_orm_columns, validate_columns_for_model
from app.models import Base
from typing import Sequence, Any, overload, Literal
from typing import TypeVar, Generic

T = TypeVar("T", bound=Base)


class _BaseRepository(Generic[T]):
    """Generic async base repository bound to a single SQLAlchemy ORM model.

    Encapsulates common persistence operations: conflict-aware inserts
    (`create_one`, `create_many`), filtered reads (`get_many`, `get_one`
    and their `*_orm` variants), single-row updates (`update_one`), and
    filtered deletes (`delete_many`).

    Subclasses set the `_model` class attribute to bind the repository to a
    specific model, e.g. `_model: Final = Gif`.

    Notes:
        - Dictionary keys in `values` and `filters` arguments must be
          column attributes of the bound model (`InstrumentedAttribute`,
          e.g. `User.id`); they are validated before the query runs.
        - Methods execute statements via the bound session but never call
          `commit()`/`rollback()` themselves — that is the caller's
          responsibility.
        - `get_many`/`get_one` return SQLAlchemy `Row` objects containing
          only the requested columns; the `*_orm` variants return full
          ORM instances of the bound model.
          
    Example:
        Assuming a subclass ``UserRepository(_BaseRepository[User])`` with
        ``_model = User``::

            repo = UserRepository(session)

            row = await repo.create_one({User.tg_id: 123456})
            rows = await repo.get_many(filters={User.id: [1, 2, 3]})
            updated = await repo.update_one(
                values={User.tg_id: 999}, filters={User.id: 1}
            )
            deleted = await repo.delete_many(filters={User.id: [2, 3]})
    """
    _model: type[T]
    
    def __init__(
            self,
            session: AsyncSession,
    ):
        """Initializes the CRUD helper.

        Args:
            session: The async SQLAlchemy session to execute queries on.
        """
        self._session = session
    
    @overload
    async def create_one(
            self,
            value: dict[InstrumentedAttribute, Any],
            ignore_conflicts: Literal[False] = False
    ) -> T:
        ...

    @overload
    async def create_one(
            self,
            value: dict[InstrumentedAttribute, Any],
            ignore_conflicts: Literal[True]
    ) -> T | None:
        ...

    async def create_one(
            self,
            value: dict[InstrumentedAttribute, Any],
            ignore_conflicts: bool = False,
    ) -> T | None:
        """Inserts a single row for the bound ORM model.

        Builds and executes an ``INSERT ... RETURNING`` statement. Column
        keys in `value` are validated against the bound model before the
        query is executed, so passing a column from an unrelated model
        fails fast instead of producing a malformed query.

        Args:
            value: Mapping of model column to the value to insert, e.g.
                ``{User.tg_id: 123456}``.
            ignore_conflicts: If True, adds ``ON CONFLICT DO NOTHING`` so a
                unique or primary-key violation is skipped instead of
                raising an error.

        Returns:
            The inserted row with all model columns populated, or None if
            `ignore_conflicts` is True and the insert was skipped due to a
            conflict.

        Raises:
            ValueError: If a key in `value` is not a column of the bound
                model.
            IntegrityError: If the insert violates a unique, foreign-key,
                or not-null constraint and `ignore_conflicts` is False.

        Example:
            Creating a GIF row::

                gif = await gif_repo.create_one(
                    {Gif.file_path: "a.mp4", Gif.file_hash: "abc"}
                )
        """
        validate_columns_for_model(
            value.keys(),
            self._model
        )

        stmt = insert(self._model).values(value)
    
        if ignore_conflicts:
            stmt = stmt.on_conflict_do_nothing()
    
        stmt = stmt.returning(self._model)
    
        result = await self._session.execute(stmt)
    
        return result.scalar_one_or_none()

    async def create_many(
            self,
            values: Sequence[dict[InstrumentedAttribute, Any]],
            ignore_conflicts: bool = False,
    ) -> list[T]:
        """Inserts multiple rows for the bound ORM model in one query.

        Unlike `create_one`, all rows are inserted via a single
        multi-row ``INSERT ... RETURNING`` statement.

        Args:
            values: Sequence of mappings, each describing one row as
                ``{column: value}``.
            ignore_conflicts: If True, adds ``ON CONFLICT DO NOTHING`` so
                rows that violate a unique or primary-key constraint are
                skipped instead of raising an error.

        Returns:
            The inserted rows with all model columns populated. If
            `ignore_conflicts` is True, skipped rows are simply absent
            from the result — the returned list may be shorter than
            `values`.

        Raises:
            ValueError: If a key in any of the `values` mappings is not a
                column of the bound model.
            IntegrityError: If an insert violates a unique, foreign-key,
                or not-null constraint and `ignore_conflicts` is False.

        Example:
            Linking one user's GIF to several tags at once, skipping ones
            that already exist::

                await user_gif_tag_repo.create_many(
                    [{UserGifTag.user_id: 1, UserGifTag.gif_id: 2, UserGifTag.tag_id: t}
                     for t in (3, 4)],
                    ignore_conflicts=True,
                )
        """
        for value in values:
            validate_columns_for_model(
                value.keys(),
                self._model
            )

        stmt = insert(self._model).values(values)

        if ignore_conflicts:
            stmt = stmt.on_conflict_do_nothing()

        stmt = stmt.returning(self._model)
        
        result = await self._session.execute(stmt)

        return list(result.scalars().all())
    
    @overload
    async def get_many(
            self,
            scalars: Literal[False] = False,
            columns: Sequence[InstrumentedAttribute] | InstrumentedAttribute | None = None,
            filters: dict[InstrumentedAttribute, Sequence[Any] | Any] | None = None,
    ) -> list[Row[tuple[Any]]]:
        ...

    @overload
    async def get_many(
            self,
            scalars: Literal[True],
            columns: Sequence[InstrumentedAttribute] | InstrumentedAttribute | None = None,
            filters: dict[InstrumentedAttribute, Sequence[Any] | Any] | None = None,
    ) -> list[Any]:
        ...

    async def get_many(
            self,
            columns: Sequence[InstrumentedAttribute] | InstrumentedAttribute | None = None,
            filters: dict[InstrumentedAttribute, Sequence[Any] | Any] | None = None,
            scalars: bool = False
    ) -> list[Row[tuple[Any]]] | list[Any]:
        """Fetches rows from the bound model's table with optional filtering.

        A filter value that is a list/tuple/set is matched with ``IN``;
        any other value is matched with ``==``.

        Args:
            columns: Column(s) to select. If None, all columns of the
                bound model are selected.
            filters: Mapping of column to value(s) to filter by, e.g.
                ``{User.id: [1, 2, 3]}``.
            scalars: If True, unwraps each result row to its single
                column value instead of returning a `Row`. Only makes
                sense when `columns` is a single column.

        Returns:
            A list of `Row` objects containing the requested columns, or
            a list of scalar values if `scalars` is True.

        Example:
            Fetching just the Telegram IDs for a set of internal user
            IDs::

                tg_ids = await user_repo.get_many(
                    columns=User.tg_id, filters={User.id: [1, 2]}, scalars=True
                )
        """
        stmt = self._build_get_stmt(
            columns=columns,
            filters=filters
        )
    
        result = await self._session.execute(stmt)
        
        if scalars:
            result = result.scalars()
            
        return list(result.all())
    
    @overload
    async def get_one(
            self,
            scalar: Literal[False] = False,
            columns: Sequence[InstrumentedAttribute] | InstrumentedAttribute | None = None,
            filters: dict[InstrumentedAttribute, Sequence[Any] | Any] | None = None
    ) -> Row[tuple[Any]] | None:
        ...
    
    @overload
    async def get_one(
            self,
            scalar: Literal[True],
            columns: Sequence[InstrumentedAttribute] | InstrumentedAttribute | None = None,
            filters: dict[InstrumentedAttribute, Sequence[Any] | Any] | None = None
    ) -> Any | None:
        ...

    async def get_one(
            self,
            columns: Sequence[InstrumentedAttribute] | InstrumentedAttribute | None = None,
            filters: dict[InstrumentedAttribute, Sequence[Any] | Any] | None = None,
            scalar: bool = False
    ) -> Row[tuple[Any]] | Any | None:
        """Fetches a single row from the bound model's table.

        Equivalent to `get_many` with a ``LIMIT 1``. If several rows match
        the filters, an arbitrary one is returned — pass filters specific
        enough to identify a single row when order matters.

        Args:
            columns: Column(s) to select. If None, all columns of the
                bound model are selected.
            filters: Mapping of column to value(s) to filter by.
            scalar: If True, unwraps the result to its single column value
                instead of returning a `Row`. Only makes sense when
                `columns` is a single column.

        Returns:
            A `Row` with the requested columns, a scalar value if `scalar`
            is True, or None if no row matches.

        Example:
            Looking up an internal user ID by Telegram ID::

                user_id = await user_repo.get_one(
                    columns=User.id, filters={User.tg_id: 123456}, scalar=True
                )
        """
        stmt = self._build_get_stmt(
            columns=columns,
            filters=filters
        ).limit(1)

        result = await self._session.execute(stmt)

        if scalar:
            return result.scalar()

        return result.first()

    async def get_many_orm(
            self,
            filters: dict[InstrumentedAttribute, Sequence[Any] | Any] | None = None,
    ) -> list[T]:
        """Fetches full ORM instances of the bound model.

        Unlike `get_many`, always selects the whole model rather than
        specific columns, returning ready-to-use ORM objects (with
        relationships accessible, subject to loading configuration).

        Args:
            filters: Mapping of column to value(s) to filter by, e.g.
                ``{Gif.file_hash: "abc"}``.

        Returns:
            A list of ORM instances of the bound model.
        """
        stmt = self._build_get_orm_stmt(
            filters=filters
        )

        result = await self._session.execute(stmt)
        
        return list(result.scalars().all())
    
    async def get_one_orm(
            self,
            filters: dict[InstrumentedAttribute, Sequence[Any] | Any] | None = None,
    ) -> T | None:
        """Fetches a single full ORM instance of the bound model.

        Equivalent to `get_many_orm` with a ``LIMIT 1``. If several rows
        match the filters, an arbitrary one is returned.

        Args:
            filters: Mapping of column to value(s) to filter by.

        Returns:
            An ORM instance of the bound model, or None if no row matches.

        Example:
            Checking whether a file with a given hash was already
            uploaded, and reusing it if so::

                gif = await gif_repo.get_one_orm(filters={Gif.file_hash: file_hash})
        """
        stmt = self._build_get_orm_stmt(
            filters=filters
        ).limit(1)

        result = await self._session.execute(stmt)

        return result.scalar_one_or_none()

    async def update_one(
            self,
            values: dict[InstrumentedAttribute, Any],
            filters: dict[InstrumentedAttribute, Any]
    ) -> T:
        """Updates exactly one row matched by `filters`.

        Args:
            values: Mapping of column to the new value, e.g.
                ``{User.tg_id: 999}``.
            filters: Mapping of column to value(s) identifying the row to
                update. Callers are responsible for making sure this
                matches exactly one row.

        Returns:
            The updated row with all model columns.

        Raises:
            ValueError: If a key in `values` is not a column of the bound
                model.
            IntegrityError: If the update violates a unique, foreign-key,
                or not-null constraint.
            NoResultFound: If `filters` matches no rows.
            MultipleResultsFound: If `filters` matches more than one row.
        """
        validate_columns_for_model(values.keys(), self._model)
        
        stmt = update(self._model).values(values).returning(self._model)
        stmt = self._add_filters_to_stmt(stmt, filters)

        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def delete_many(
            self,
            filters: dict[InstrumentedAttribute, Sequence[Any] | Any]
    ) -> list[T]:
        """Deletes all rows matched by `filters`.

        Args:
            filters: Mapping of column to value(s) identifying the rows to
                delete, e.g. ``{User.id: [2, 3]}``.

        Returns:
            The deleted rows with all model columns, in whatever order the
            database returned them. An empty list means nothing matched
            `filters`.
        """
        stmt = delete(self._model)
        stmt = self._add_filters_to_stmt(stmt, filters)
        
        stmt = stmt.returning(self._model)
        
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    def _add_filters_to_stmt[T_stmt: Select | Update | Delete | Insert](
            self,
            stmt: T_stmt,
            filters: dict[InstrumentedAttribute, Sequence[Any] | Any],
    ) -> T_stmt:
        """Applies WHERE conditions from `filters` to a statement.

        A filter value that is a list/tuple/set is matched with ``IN``;
        any other value is matched with ``==``.

        Args:
            stmt: The `Select`, `Update`, `Delete`, or `Insert` statement
                to add conditions to.
            filters: Mapping of column to value(s) to filter by.

        Returns:
            The same statement with the corresponding WHERE clauses added.

        Raises:
            ValueError: If a key in `filters` is not a column of the bound
                model.
        """
        for column, values in filters.items():
            if not is_valid_column_for_model(column, self._model):
                raise ValueError(f"Expected a column of model {self._model.__name__} as a filter key. "
                                 f"Got {type(column)}: {column}.")
            if not isinstance(values, (list, tuple, set)):
                stmt = stmt.where(column == values)
            else:
                stmt = stmt.where(column.in_(values))

        return stmt

    def _build_get_stmt(
            self,
            columns: Sequence[InstrumentedAttribute] | InstrumentedAttribute | None = None,
            filters: dict[InstrumentedAttribute, Sequence[Any] | Any] | None = None,
    ) -> Select:
        """Builds a `Select` statement for the given columns and filters.

        Shared by `get_many` and `get_one`.

        Args:
            columns: Column(s) to select. If None, all columns of the
                bound model are selected.
            filters: Mapping of column to value(s) to filter by.

        Returns:
            The constructed `Select` statement.

        Raises:
            ValueError: If a column in `columns` or a key in `filters` is
                not a column of the bound model.
        """
        if columns and isinstance(columns, InstrumentedAttribute):
            columns = (columns,)

        if not columns:
            columns = get_orm_columns(self._model)
        else:
            validate_columns_for_model(columns, self._model)

        stmt = select(*columns)

        if filters:
            stmt = self._add_filters_to_stmt(stmt, filters)

        return stmt

    def _build_get_orm_stmt(
            self,
            filters: dict[InstrumentedAttribute, Sequence[Any] | Any] | None = None,
    ) -> Select:
        """Builds a `Select` statement over the full bound model.

        Shared by `get_many_orm` and `get_one_orm`.

        Args:
            filters: Mapping of column to value(s) to filter by.

        Returns:
            The constructed `Select` statement.

        Raises:
            ValueError: If a key in `filters` is not a column of the bound
                model.
        """
        stmt = select(self._model)

        if filters:
            stmt = self._add_filters_to_stmt(stmt, filters)

        return stmt
