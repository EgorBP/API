from datetime import datetime, timezone
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


TagString = Annotated[
    str, 
    StringConstraints(
        min_length=1, 
        max_length=100, 
        strip_whitespace=True,
    )
]
"""
Type alias for valid tag strings.

Validates that the tag is a non-empty string stripped of leading/trailing whitespace, 
with a length between 1 and 100 characters.
"""


class RawTagsOut(BaseModel):
    """A flat list of tag strings, with a count."""
    tags: list[TagString]
    count: int
    
    model_config = ConfigDict(from_attributes=True)


class PopularTagsOut(BaseModel):
    """The cached site-wide popular tags list.

    Attributes:
        updated_at: When this list was last recalculated by the
            background task.
    """
    tags: list[TagString]
    count: int
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True)
