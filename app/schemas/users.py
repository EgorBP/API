from pydantic import BaseModel
from enum import Enum


# ===== Пользователь =====
class UserBase(BaseModel):
    tg_user_id: int

class UserCreate(UserBase):
    pass

class UserOut(UserBase):
    id: int

    model_config = {
        "from_attributes": True
    }


class UserIdSource(str, Enum):
    db = "db"
    tg = "tg"
