from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, Field


class GifBase(BaseModel):
    """Fields common to all GIF schemas: the tags assigned to it."""
    tags: set[str]


class GifOut(GifBase):
    """A GIF as returned to a client, including its own tags."""
    id: int
    file_path: str

    model_config = ConfigDict(from_attributes=True)


class RawGifOut(BaseModel):
    """A GIF as returned to a client, without any tag information."""
    id: int
    file_path: str

    model_config = ConfigDict(from_attributes=True)


class PopularGifsOut(BaseModel):
    """The cached site-wide popular GIFs list.

    Attributes:
        updated_at: When this list was last recalculated by the
            background task.
    """
    gifs: list[RawGifOut]
    count: int
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = ConfigDict(from_attributes=True)
