from pydantic import BaseModel, ConfigDict


class UserBase(BaseModel):
    """Fields common to all user schemas: their Telegram ID."""
    tg_id: int


class UserOut(UserBase):
    """A user as returned to a client."""
    id: int

    model_config = ConfigDict(from_attributes=True)
