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


def get_orm_columns(model: type[Base]) -> tuple[InstrumentedAttribute]:
    """
    Возвращает список всех колонок SQLAlchemy-модели в ORM формате.

    :param model: SQLAlchemy-модель (например, User).
    :return: список колонок модели в формате [Model.col1, Model.col2, ...].
    """
    return tuple(getattr(model, column.key) for column in inspect(model).columns)
