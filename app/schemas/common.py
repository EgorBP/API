from enum import Enum
from typing import TypeVar

from pydantic import BaseModel, Field

DataT = TypeVar("DataT")
CursorT = TypeVar("CursorT")


class CursorPaginationMeta[CursorT](BaseModel):
    """Pagination metadata for a cursor-paginated response.

    Attributes:
        limit: The page size that was requested.
        next_cursor: Value to pass as the next page's cursor, or None if
            there is no next page.
        has_next: Whether another page of results is available.
    """
    limit: int
    next_cursor: CursorT | None = None
    has_next: bool


class CursorPaginatedResponse[DataT, CursorT](BaseModel):
    """A single page of results plus its pagination metadata."""
    data: list[DataT] = Field(default_factory=list)
    pagination: CursorPaginationMeta[CursorT]


class SortOrder(str, Enum):
    """Sort direction for ID-based ordering and cursor pagination."""
    ASC = "asc"
    DESC = "desc"
