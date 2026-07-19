from fastapi import Form
from pydantic import BaseModel, ConfigDict


# ===== Гифка =====
class GifBase(BaseModel):
    tags: set[str]

class GifCreate(GifBase):
    @classmethod
    def as_form(cls, tags: set[str] = Form()):
        return cls(tags=tags)
    
class GifUpdate(GifBase):
    pass

class GifOut(GifBase):
    id: int
    file_path: str

    model_config = ConfigDict(from_attributes=True)
