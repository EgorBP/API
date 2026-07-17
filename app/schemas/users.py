from pydantic import BaseModel
from enum import Enum


# ===== Пользователь =====
class UserBase(BaseModel):
    pass

class UserCreate(UserBase):
    pass

class UserOut(UserBase):
    id: int

    model_config = {
        "from_attributes": True
    }
