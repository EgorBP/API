from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, Field


class TagBase(BaseModel):
    tag: str


class TagCreate(TagBase):
    pass


class TagOut(TagBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class RawTagsOut(BaseModel):
    tags: list[str]
    count: int
    
    model_config = ConfigDict(from_attributes=True)


class PopularTagsOut(BaseModel):
    tags: list[str]
    count: int
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True)
