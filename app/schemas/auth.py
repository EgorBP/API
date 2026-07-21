from pydantic import BaseModel
from typing import Optional


class TelegramAuthSchema(BaseModel):
    id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None
    auth_date: int
    hash: str


class TokenResponseSchema(BaseModel):
    access_token: str
    token_type: str = "bearer"
