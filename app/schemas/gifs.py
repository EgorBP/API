from pydantic import BaseModel


# ===== Гифка =====
class GifBase(BaseModel):
    tg_gif_id: str

class GifCreate(GifBase):
    pass

class GifUpdate(BaseModel):
    tags: set[str]

class GifOut(GifBase):
    id: int
    tags: set[str]

    model_config = {
        "from_attributes": True
    }

