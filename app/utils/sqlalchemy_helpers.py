from collections.abc import Iterable

from sqlalchemy import inspect
from sqlalchemy.orm.attributes import InstrumentedAttribute

from app.models import Base


def is_valid_column_for_model(
        column: InstrumentedAttribute, 
        model: type[Base]
) -> bool:
    """Checks whether `column` is an ORM attribute of `model`.

    Args:
        column: The object to check, expected to be an ORM column
            attribute such as `User.id`.
        model: The ORM model class the column should belong to.

    Returns:
        True if `column` is an `InstrumentedAttribute` belonging to
        `model`, False otherwise.
    """
    return isinstance(column, InstrumentedAttribute) and column.class_ == model


def validate_columns_for_model(
        columns: Iterable[InstrumentedAttribute] | InstrumentedAttribute, 
        model: type[Base]
) -> None:
    """Validates that one or more columns all belong to a given model.

    Args:
        columns: A single column or an iterable of columns to validate,
            e.g. `User.id` or `[User.id, User.name]`.
        model: The ORM model class the columns should belong to.

    Raises:
        ValueError: If any column is not an `InstrumentedAttribute`
            belonging to `model`.
    """
    if isinstance(columns, InstrumentedAttribute):
        columns = (columns,)
    
    for column in columns:
        if not is_valid_column_for_model(column, model):
            raise ValueError(f"Expected a column of model {model.__name__} in the column list. "
                             f"Got {type(column)}: {column}.")


def get_orm_columns(
        model: type[Base]
) -> tuple[InstrumentedAttribute]:
    """Returns every column of an ORM model as attribute objects.

    Args:
        model: The ORM model class, e.g. `User`.

    Returns:
        The model's columns as ORM attributes, e.g.
        ``(User.id, User.tg_id)``.
    """
    return tuple(getattr(model, column.key) for column in inspect(model).columns)
