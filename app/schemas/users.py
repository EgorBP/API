from pydantic import BaseModel, ConfigDict


# ===== Пользователь =====
class UserBase(BaseModel):
    pass

class UserCreate(UserBase):
    pass

class UserOut(UserBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
