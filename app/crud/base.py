from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy import select, update, delete, inspect
from sqlalchemy.dialects.postgresql import insert
from app.utils import is_valid_column_for_model, get_orm_columns
from typing import Sequence, Any
from app.models import Base


class _BaseCRUD:
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
        - Во многих методах ожидается, что ключи словарей `values` и `filters` — это именно
          колонковые атрибуты модели (InstrumentedAttribute). Перед выполнением запросов
          производится валидация колонок.
        - Методы выполняют SQL-запросы через `self.async_session.execute(...)`, но НЕ выполняют
          `commit()` автоматически. За фиксацию транзакции (commit/rollback) отвечает вызывающий код.
        - Возвращаемые значения типичны для асинхронного SQLAlchemy:
            - `create_instance` / `update_instance` возвращают одну строку (Row) или None.
            - `get_instances` возвращает список строк (List[Row]).
            - `delete_instances` возвращает количество удалённых строк (int).

    Пример использования:
    
        crud = _BaseCRUD(async_session=session, model=User)
        
        # вставка
        
        row = await crud.create_instance({User.email: "a@example.com", User.name: "A"})
        
        # выборка
        
        rows = await crud.get_instances(filters={User.is_active: True})
        
        # обновление
        
        updated = await crud.update_instance(instance_id=1, values={User.name: "B"})
        
        # удаление
        
        deleted_count = await crud.delete_instances(filters={User.id: [2, 3]})
    """
    def __init__(
            self,
            async_session: AsyncSession,
            model: type[Base],
    ):
        """
        :param async_session: Объект асинхронной сессии SQLAlchemy.
        :param model: SQLAlchemy модель.
        """
        self.async_session = async_session
        self.model = model

    async def create_instance(
            self,
            values: dict[InstrumentedAttribute, Any],
    ):
        """
        Создаёт новую запись в таблице или возвращает существующую при конфликте.

        Метод выполняет вставку (INSERT) в таблицу, соответствующую текущей модели ORM.
        В случае конфликта по переданным колонкам (ключи словаря `values`) выполняется
        обновление первой найденной не autoincrement колонки таблицы на саму себя и возврат всех колонок модели.  
        
        Если у таблицы все колонки являются первичными ключами, метод не может быть выполнен.

        :param values: Словарь {column: value}, где column — колонка модели (InstrumentedAttribute),
                       а value — значение для вставки.
        :return: Строка результата (Row), содержащая значения всех колонок модели после операции. 
        """
        columns = get_orm_columns(self.model)
        not_autoincrement_key_index = -1
        for i, col in enumerate(inspect(self.model).columns):
            if not col.autoincrement or bool(col.foreign_keys) or not col.primary_key and col.autoincrement == 'auto':
                not_autoincrement_key_index = i
                break
                
        unique_cols = []
        for col in values.keys():
            if col.unique or col.primary_key:
                unique_cols.append(col)

        if not_autoincrement_key_index == -1:
            raise ValueError(f"Все колонки текущей таблицы {self.model.__tablename__} - primary_key. "
                             "Данный метод не может работать с такими таблицами.")
        
        for column in values:
            if not is_valid_column_for_model(column, self.model):
                raise ValueError(f"В ключе для вставки ожидается колонка модели {self.model.__name__}. "
                                 f"Вы передали {type(column)}, а именно {column}.")

        insert_stmt = insert(self.model).values(values)
        if unique_cols:
            col_name = columns[not_autoincrement_key_index].name
            stmt = insert_stmt.on_conflict_do_update(
                index_elements=unique_cols,
                set_={col_name: insert_stmt.excluded[col_name]},
            ).returning(*columns)
        else:
            stmt = insert_stmt.returning(*columns)
            
        result = await self.async_session.execute(stmt)

        return result.fetchone()

    async def get_instances(
            self,
            columns: Sequence[InstrumentedAttribute] | InstrumentedAttribute | None = None,
            filters: dict[InstrumentedAttribute, Sequence[Any] | Any] | None = None
    ):
        """
        Универсальная функция получения записей с фильтрацией по колонкам.
    
        :param columns: Колонки для возврата. Если None — вернутся все.
        :param filters: Словарь {column: value}, где column — колонка модели (InstrumentedAttribute),
                       а value — значение для фильтрации.
        :return: Список объектов с выбранными колонками.
        """
        if columns and not isinstance(columns, (list, tuple)):
            columns = (columns, )
    
        if not columns:
            columns = get_orm_columns(self.model)
        else:
            for column in columns:
                if not is_valid_column_for_model(column, self.model):
                    raise ValueError(f"В списке колонок ожидается колонка модели {self.model.__name__}. "
                                     f"Вы передали {type(column)}, а именно {column}.")
        
        stmt = select(*columns)
    
        if filters:
            for column, values in filters.items():
                if not is_valid_column_for_model(column, self.model):
                    raise ValueError(f"В ключе для фильтрации ожидается колонка модели {self.model.__name__}. "
                                     f"Вы передали {type(column)}, а именно {column}.")
                if not isinstance(values, (list, tuple)):
                    values = (values,)
    
                stmt = stmt.where(column.in_(values))
    
        result = await self.async_session.execute(stmt)
        return result.all()
    
    async def update_instance(
            self,
            instance_id: int | None,
            values: dict[InstrumentedAttribute, Any],
            *,
            filters: dict[InstrumentedAttribute, Any] | None = None,
    ):
        """
        Универсальная функция обновления одной записи в таблице модели.

        Метод обновляет **только одну запись**: либо по первичному ключу (`instance_id`), 
        либо по заданным фильтрам (`filters`). Возвращает все колонки обновлённой записи после выполнения операции.

        :param instance_id: Значение первичного ключа записи для обновления. Если указано, фильтры игнорируются.
        :param values: Словарь {column: value}, где column — колонка модели (InstrumentedAttribute),
                       а value — новое значение для обновления.
        :param filters: Словарь {column: value} для фильтрации обновляемых записей, используется если `instance_id` не задан. Воз
        :return: Row с колонками модели после обновления, или None, если запись не найдена.
        """
        
        for column in values:
            if not is_valid_column_for_model(column, self.model):
                raise ValueError(f"В ключе для вставки ожидается колонка модели {self.model.__name__}. "
                                 f"Вы передали {type(column)}, а именно {column}.")
        
        columns = get_orm_columns(self.model)
        
        if instance_id is not None:
            stmt = update(self.model).where(inspect(self.model).primary_key[0] == instance_id).values(values).returning(*columns)
            result = await self.async_session.execute(stmt)
            return result.fetchone()        

        if not filters:
            raise ValueError("Нужно указать либо instance_id, либо фильтры для удаления.")

        stmt = update(self.model).returning(*columns)
        for column, id_ in filters.items():
            if not is_valid_column_for_model(column, self.model):
                raise ValueError(f"В ключе для фильтрации ожидается колонка модели {self.model.__name__}. "
                                 f"Вы передали {type(column)}, а именно {column}.")

            stmt = stmt.where(column == id_)

        result = await self.async_session.execute(stmt)
        # noinspection PyUnresolvedReferences
        return result.fetchone()

    async def delete_instances(
            self,
            instance_id: int | None = None,
            *,
            filters: dict[InstrumentedAttribute, Sequence[Any] | Any] | None = None,
    ) -> int:
        """
        Универсальная функция удаления записей.
    
        Можно удалить запись по первому найденному первичному ключу (instance_id) или по фильтрам.
        Приоритет имеет первичный ключ.
    
        :param instance_id: Первичный ключ записи для удаления.
        :param filters: Словарь {column: value}, где column — колонка модели (InstrumentedAttribute),
                       а value — значение для удаления.
        :return: Количество удалённых строк.
        """
        if instance_id is not None:
            stmt = delete(self.model).where(inspect(self.model).primary_key[0] == instance_id)
            result = await self.async_session.execute(stmt)
            # noinspection PyTypeChecker
            return result.rowcount
    
        if not filters:
            raise ValueError("Нужно указать либо instance_id, либо фильтры для удаления.")

        stmt = delete(self.model)
        for column, values in filters.items():
            if not is_valid_column_for_model(column, self.model):
                raise ValueError(f"В ключе для фильтрации ожидается колонка модели {self.model.__name__}. "
                                 f"Вы передали {type(column)}, а именно {column}.")
            if not isinstance(values, (list, tuple)):
                values = (values,)
    
            stmt = stmt.where(column.in_(values))
        
        result = await self.async_session.execute(stmt)
        # noinspection PyUnresolvedReferences
        return result.rowcount
