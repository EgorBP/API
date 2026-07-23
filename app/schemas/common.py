from enum import Enum
from pydantic import BaseModel
from typing import Generic, TypeVar

DataT = TypeVar("DataT")
CursorT = TypeVar("CursorT")


class CursorPaginationMeta(BaseModel, Generic[CursorT]):
    limit: int
    next_cursor: CursorT | None = None
    has_next: bool


class CursorPaginatedResponse(BaseModel, Generic[DataT, CursorT]):
    data: list[DataT]
    pagination: CursorPaginationMeta[CursorT] | None = None


class SortOption(str, Enum):
    NEW = "new"
    OLD = "old"
