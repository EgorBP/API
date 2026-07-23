from pydantic import BaseModel, ConfigDict


class UserBase(BaseModel):
    tg_id: int


class UserCreate(UserBase):
    pass


class UserOut(UserBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
