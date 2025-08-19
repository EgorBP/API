from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import InstrumentedAttribute
from utils import is_valid_column_for_model, get_all_columns
from typing import Sequence

"""
Так как функции создания могут принимать различное количество параметров различных типов
и для их использования нужно знать точную колонку для on_conflict_do_nothing(), 
было принято решение не создавать универсальную функцию для этого, так как это 
может запутать людей, которые будут разбираться с кодом в будущем 
(хоть этого и можно было избежать сделая ее приватным методом класса)
"""

def get_instances(
        session: Session,
        model: type,
        columns: Sequence[InstrumentedAttribute] | InstrumentedAttribute | None = None,
        filters: dict[InstrumentedAttribute, Sequence[int] | int] | None = None
):
    """
    Универсальная функция получения записей с фильтрацией по колонкам.

    :param session: объект сессии SQLAlchemy.
    :param model: SQLAlchemy модель.
    :param columns: колонки для возврата. Если None — вернутся все.
    :param filters: словарь {column: values}, где values — список, кортеж или одно значение.
    :return: список объектов с выбранными колонками.
    """
    if columns and not isinstance(columns, (list, tuple)):
        columns = (columns, )

    if not columns:
        columns = get_all_columns(model)
    else:
        for column in columns:
            if not is_valid_column_for_model(column, model):
                raise ValueError(f"В списке колонок ожидается колонка таблицы {model.__name__}. "
                                 f"Вы передали {type(column)}, а именно {column}.")

    query = session.query(*columns)

    if filters:
        for column, values in filters.items():
            if not is_valid_column_for_model(column, model):
                raise ValueError(f"В ключе для фильтрации ожидается колонка таблицы {model.__name__}. "
                                 f"Вы передали {type(column)}, а именно {column}.")
            if not isinstance(values, (list, tuple)):
                values = (values,)

            for value in values:
                if not isinstance(value, column.type.python_type):
                    raise ValueError(f'Значением колонки {column} должен быть класс {column.type.python_type},'
                                     f' а не {type(value)} ({value}).')

            query = query.filter(column.in_(values))

    return query.all()


def delete_instances(
        session: Session,
        model: type,
        filters: dict[InstrumentedAttribute, Sequence[int | str] | int | str] | None = None,
        instance_id: int | None = None
) -> int | bool:
    """
    Универсальная функция удаления записей.

    Можно удалить запись по первичному ключу (instance_id) или по фильтрам.

    :param session: объект сессии SQLAlchemy.
    :param model: SQLAlchemy модель.
    :param filters: словарь {column: values} для массового удаления.
    :param instance_id: первичный ключ записи для удаления.
    :return: True/False если удаляется одна запись по ID,
             или количество удалённых строк при удалении по фильтрам.
    """
    if instance_id is not None:
        instance = session.get(model, instance_id)
        if not instance:
            return False
        session.delete(instance)
        session.commit()
        return True

    if not filters:
        raise ValueError("Нужно указать либо instance_id, либо фильтры для удаления.")

    query = session.query(model)
    for column, values in filters.items():
        if not is_valid_column_for_model(column, model):
            raise ValueError(f"В ключе для фильтрации ожидается колонка таблицы {model.__name__}. "
                             f"Вы передали {type(column)}, а именно {column}.")
        if not isinstance(values, (list, tuple)):
            values = (values,)

        for value in values:
            if not isinstance(value, column.type.python_type):
                raise ValueError(f'Значением колонки {column} должен быть класс {column.type.python_type},'
                                 f' а не {type(value)} ({value}).')

        query = query.filter(column.in_(values))

    deleted_count = query.delete(synchronize_session=False)
    session.commit()
    return deleted_count
