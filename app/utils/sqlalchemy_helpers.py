from typing import Iterable
from sqlalchemy import inspect
from sqlalchemy.orm.attributes import InstrumentedAttribute
from app.models import Base


def is_valid_column_for_model(column: InstrumentedAttribute, model: type[Base]) -> bool:
    """
    Проверяет, что переданный ключ является колонкой (атрибутом модели),
    и принадлежит указанной модели.

    :param column: проверяемый объект (ожидается ORM-атрибут, например User.id).
    :param model: класс ORM-модели (например User).
    """

    return isinstance(column, InstrumentedAttribute) and column.class_ == model


def validate_columns_for_model(
        columns: Iterable[InstrumentedAttribute] | InstrumentedAttribute, 
        model: type[Base]
) -> None:
    """
    Проверяет, что переданные колонки являются ORM-атрибутами указанной модели.

    Если хотя бы одна колонка не принадлежит модели или не является
    `InstrumentedAttribute`, возбуждается `ValueError`.

    :param columns: Одна колонка модели или последовательность колонок
                    (например `User.id` или `[User.id, User.name]`).
    :param model: Класс ORM-модели, которой должны принадлежать колонки
                  (например `User`).
    :raises ValueError: Если хотя бы одна из переданных колонок не принадлежит
                        указанной модели или не является ORM-атрибутом.
    """    
    if isinstance(columns, InstrumentedAttribute):
        columns = (columns,)
    
    for column in columns:
        if not is_valid_column_for_model(column, model):
            raise ValueError(f"В списке колонок ожидается колонка модели {model.__name__}. "
                             f"Вы передали {type(column)}, а именно {column}.")


def get_orm_columns(model: type[Base]) -> tuple[InstrumentedAttribute]:
    """
    Возвращает список всех колонок SQLAlchemy-модели в ORM формате.

    :param model: SQLAlchemy-модель (например, User).
    :return: список колонок модели в формате [Model.col1, Model.col2, ...].
    """
    return tuple(getattr(model, column.key) for column in inspect(model).columns)
