from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables and `.env`.

    Values are read from the OS environment first, falling back to the
    `.env` file specified in `model_config`. Unknown keys in the
    environment are ignored rather than raising an error.

    Attributes:
        DEV_MODE: Enable dev endpoints.
        POSTGRES_USER: PostgreSQL username.
        POSTGRES_PASSWORD: PostgreSQL password.
        POSTGRES_DB: PostgreSQL database name.
        POSTGRES_HOST: PostgreSQL host.
        POSTGRES_PORT: PostgreSQL port.
        REDIS_HOST: Redis host.
        REDIS_PORT: Redis port.
        BOT_API_SECRET: Shared secret used to authenticate the Telegram bot
            against the internal `/bot` API.
        BOT_TOKEN: Telegram bot token, used to verify Telegram Login Widget
            data.
        JWT_SECRET_KEY: Secret key used to sign and verify JWTs.
        JWT_ALGORITHM: Algorithm used for JWT signing (e.g. "HS256").
        ACCESS_TOKEN_EXPIRE_MINUTES: Access token lifetime, in minutes.
        REFRESH_TOKEN_EXPIRE_DAYS: Refresh token lifetime, in days.
        BASE_DIR: Absolute path to the project root.
        MEDIA_DIR: Absolute path to the directory where GIF/MP4 files are
            stored.
    """
    DEV_MODE: bool = False
    
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int

    REDIS_HOST: str
    REDIS_PORT: int

    BOT_API_SECRET: str
    BOT_TOKEN: str

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int

    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    MEDIA_DIR: Path = BASE_DIR / "media" / "gifs"

    model_config = SettingsConfigDict(
        env_file="envs/.env",
        extra="ignore"
    )


settings = Settings()
