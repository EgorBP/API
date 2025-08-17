from typing import Any
from sqlalchemy.orm.attributes import InstrumentedAttribute


def is_valid_column_for_model(column: InstrumentedAttribute, model: type) -> bool:
    """
    Проверяет, что переданный ключ является колонкой (атрибутом модели),
    и принадлежит указанной модели.

    :param column: проверяемый объект (ожидается ORM-атрибут, например User.id).
    :param model: класс ORM-модели (например User).
    """

    return isinstance(column, InstrumentedAttribute) and column.class_ == model
