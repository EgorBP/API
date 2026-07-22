from pydantic import BaseModel, ConfigDict


class TagBase(BaseModel):
    tag: str


class TagCreate(TagBase):
    pass


class TagOut(TagBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
