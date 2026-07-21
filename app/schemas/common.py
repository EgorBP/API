from pydantic import BaseModel
from typing import Generic, TypeVar, Any
from app.schemas.users import UserOut
from app.schemas.gifs import GifOut

DataT = TypeVar("DataT")
CursorT = TypeVar("CursorT")


class CursorPaginationMeta(BaseModel, Generic[CursorT]):
    limit: int
    next_cursor: CursorT | None = None
    has_next: bool


class CursorPaginatedResponse(BaseModel, Generic[DataT, CursorT]):
    data: list[DataT]
    pagination: CursorPaginationMeta[CursorT] | None = None
