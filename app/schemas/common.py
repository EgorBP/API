from enum import Enum
from pydantic import BaseModel, Field
from typing import Generic, TypeVar

DataT = TypeVar("DataT")
CursorT = TypeVar("CursorT")


class CursorPaginationMeta(BaseModel, Generic[CursorT]):
    limit: int
    next_cursor: CursorT | None = None
    has_next: bool


class CursorPaginatedResponse(BaseModel, Generic[DataT, CursorT]):
    data: list[DataT] = Field(default_factory=list)
    pagination: CursorPaginationMeta[CursorT]


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"
