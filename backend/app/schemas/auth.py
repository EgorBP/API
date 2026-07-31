
from pydantic import BaseModel


class TelegramAuthSchema(BaseModel):
    """Payload sent by the Telegram Login Widget after a successful login."""
    id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None
    auth_date: int
    hash: str


class TokenResponseSchema(BaseModel):
    """An access/refresh token pair returned after login or refresh."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequestSchema(BaseModel):
    """Request body for exchanging a refresh token for a new token pair."""
    refresh_token: str
