from enum import Enum
from pydantic import BaseModel, ConfigDict


class UserBase(BaseModel):
    tg_id: int


class UserCreate(UserBase):
    pass


class UserOut(UserBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class UserStatus(str, Enum):
    active = "active"
    banned = "banned"
    deleted_or_not_found = "deleted_or_not_found"
