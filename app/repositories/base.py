from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, inspect, Row, Select, Update, Delete, Insert
from app.utils import is_valid_column_for_model, get_orm_columns, validate_columns_for_model
from app.models import Base
from typing import Sequence, Any, overload, Literal
from typing import TypeVar, Generic

T = TypeVar("T", bound=Base)


# TODO: update dockstring
class _BaseCRUD(Generic[T]):
    """
    Базовый утилитный класс для выполнения типичных операций CRUD (Create, Read, Update, Delete)
    над одной SQLAlchemy ORM-моделью в асинхронном контексте.

    Класс инкапсулирует часто используемые шаблоны запросов: вставку с обработкой конфликтов
    (`create_instance`), выборку с универсальными фильтрами (`get_instances`), обновление одной
    записи (`update_instance`) и удаление записей (`delete_instances`).

    Важные моменты:
        - Экземпляр класса привязывается к конкретной ORM-модели и асинхронной сессии:
            - async_session: AsyncSession — асинхронная сессия SQLAlchemy.
            - model: Subclass[Base] — класс ORM-модели.
        - Во всех методах ожидается, что ключи словарей `values` и `filters` — это именно
          колонковые атрибуты модели (InstrumentedAttribute). Перед выполнением запросов
          производится валидация колонок.
        - Методы выполняют SQL-запросы через `self.async_session.execute(...)`, но НЕ выполняют
          `commit()` автоматически. За фиксацию транзакции (commit/rollback) отвечает вызывающий код.
        - Возвращаемые значения типичны для асинхронного SQLAlchemy:
            - `create_instance` / `update_instance` возвращают одну строку (Row) или None.
            - `get_instances` возвращает список строк (List[Row]).
            - `delete_instances` возвращает количество удалённых строк (int).

    Пример использования:
    
        repositories = _BaseCRUD(async_session=session, model=User)
        
        # вставка
        
        row = await repositories.create_instance({User.email: "a@example.com", User.name: "A"})
        
        # выборка
        
        rows = await repositories.get_instances(filters={User.is_active: True})
        
        # обновление
        
        updated = await repositories.update_instance(instance_id=1, values={User.name: "B"})
        
        # удаление
        
        deleted_count = await repositories.delete_instances(filters={User.id: [2, 3]})
    """
    _model: type[T]
    
    def __init__(
            self,
            session: AsyncSession,
    ):
        """
        :param session: Объект асинхронной сессии SQLAlchemy.
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
        """

        :param value: Словарь {column: value}, где column — колонка модели (InstrumentedAttribute),
                       а value — значение для вставки.
        :return: Строка результата (Row), содержащая значения всех колонок модели после операции. 
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
        """
        Создаёт несколько записей в таблице текущей ORM-модели.

        Метод выполняет массовую вставку (INSERT) нескольких записей за один
        запрос к базе данных и возвращает созданные строки.

        В отличие от `create_one`, метод не выполняет обработку конфликтов
        уникальности. Если одна из записей нарушает ограничение таблицы
        (например UNIQUE или PRIMARY KEY), операция вставки завершится ошибкой.

        :param values: Список словарей {column: value}, где column — колонка
                       модели ORM (`InstrumentedAttribute`), а value —
                       значение для вставки.
        :param ignore_conflicts: Пропускает уже имеющиеся записи. 
                                 Применяет к запросу метод on_conflict_do_nothing().

        :return: Список строк результата (`Row`), содержащих значения всех
                 колонок модели после вставки.

        :raises ValueError: Если переданная колонка не принадлежит текущей
                            ORM-модели.
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
        """
        Универсальный метод получения записей с фильтрацией по колонкам.
    
        :param columns: Колонки для возврата. Если None — вернутся все.
        :param filters: Словарь {column: value}, где column — колонка модели (InstrumentedAttribute),
                       а value — значение для фильтрации.
        :param scalars: Будет ли применен scalars() к результату.
        :return: Список объектов с выбранными колонками.
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
        """
        Универсальный метод получения записей с фильтрацией по колонкам.

        :param columns: Колонки для возврата. Если None — вернутся все.
        :param filters: Словарь {column: value}, где column — колонка модели (InstrumentedAttribute),
                       а value — значение для фильтрации.
        :param scalars: Будет ли применен scalars() к результату.
        :return: Список объектов с выбранными колонками.
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
        """
        Универсальный метод получения ORM модели текущей таблицы.

        :param filters: Словарь {column: value}, где column — колонка модели (InstrumentedAttribute),
                       а value — значение для фильтрации.
        :return: Список объектов с выбранными колонками.
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
        """
        Универсальный метод получения записей с фильтрацией по колонкам.

        :param columns: Колонки для возврата. Если None — вернутся все.
        :param filters: Словарь {column: value}, где column — колонка модели (InstrumentedAttribute),
                       а value — значение для фильтрации.
        :param scalars: Будет ли применен scalars() к результату.
        :return: Список объектов с выбранными колонками.
        """
        stmt = self._build_get_orm_stmt(
            filters=filters
        ).limit(1)

        result = await self._session.execute(stmt)

        return result.scalar_one_or_none()

    async def update_one(
            self,
            instance_id: int | None,
            values: dict[InstrumentedAttribute, Any],
            *,
            filters: dict[InstrumentedAttribute, Any] | None = None,
    ) -> T:
        """
        Универсальный метод обновления одной записи в таблице модели.

        Метод обновляет **только одну запись**: либо по первичному ключу (`instance_id`), 
        либо по заданным фильтрам (`filters`). Возвращает все колонки обновлённой записи после выполнения операции.

        :param instance_id: Значение первичного ключа записи для обновления. Если указано, фильтры игнорируются.
        :param values: Словарь {column: value}, где column — колонка модели (InstrumentedAttribute),
                       а value — новое значение для обновления.
        :param filters: Словарь {column: value} для фильтрации обновляемых записей, используется если `instance_id` не задан.
        :return: Row с колонками модели после обновления, или None, если запись не найдена.
        """
        validate_columns_for_model(values.keys(), self._model)
        
        if instance_id is not None:
            stmt = update(self._model).where(inspect(self._model).primary_key[0] == instance_id).values(values).returning(self._model)
            result = await self._session.execute(stmt)
            return result.scalar_one()

        if not filters:
            raise ValueError("Нужно указать либо instance_id, либо фильтры для изменения.")

        stmt = update(self._model).returning(self._model)
            
        stmt = self._add_filters_to_stmt(stmt, filters)

        result = await self._session.execute(stmt)
        
        return result.scalar_one()

    async def delete_many(
            self,
            instance_id: int | None = None,
            *,
            filters: dict[InstrumentedAttribute, Sequence[Any] | Any] | None = None,
    ) -> list[T] | None:
        """
        Универсальный метод удаления записей.
    
        Можно удалить запись по первому найденному первичному ключу (instance_id) или по фильтрам.
        Приоритет имеет первичный ключ.
    
        :param instance_id: Первичный ключ записи для удаления.
        :param filters: Словарь {column: value}, где column — колонка модели (InstrumentedAttribute),
                       а value — значение для удаления.
        :return: Количество удалённых строк.
        """
        if instance_id is not None:
            stmt = delete(self._model).where(inspect(self._model).primary_key[0] == instance_id)
        elif filters is not None:
            stmt = delete(self._model)
            stmt = self._add_filters_to_stmt(stmt, filters)
        else:
            raise ValueError("Нужно указать либо instance_id, либо фильтры для удаления.")
        
        stmt = stmt.returning(self._model)
        
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    def _add_filters_to_stmt[T_stmt: Select | Update | Delete | Insert](
            self,
            stmt: T_stmt,
            filters: dict[InstrumentedAttribute, Sequence[Any] | Any],
    ) -> T_stmt:
        for column, values in filters.items():
            if not is_valid_column_for_model(column, self._model):
                raise ValueError(f"В ключе для фильтрации ожидается колонка модели {self._model.__name__}. "
                                 f"Вы передали {type(column)}, а именно {column}.")
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
        stmt = select(self._model)

        if filters:
            stmt = self._add_filters_to_stmt(stmt, filters)

        return stmt
