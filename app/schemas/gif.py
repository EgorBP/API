from pydantic import BaseModel, ConfigDict


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
