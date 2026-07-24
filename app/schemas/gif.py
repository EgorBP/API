from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, Field


class GifBase(BaseModel):
    tags: set[str]


class GifCreate(GifBase):
    pass

    
class GifUpdate(GifBase):
    id: int


class GifOut(GifBase):
    id: int
    file_path: str

    model_config = ConfigDict(from_attributes=True)


class RawGifOut(BaseModel):
    id: int
    file_path: str

    model_config = ConfigDict(from_attributes=True)


class PopularGifsOut(BaseModel):
    gifs: list[RawGifOut]
    count: int
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = ConfigDict(from_attributes=True)
