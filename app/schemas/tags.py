from pydantic import BaseModel


# ===== Тег =====
class TagBase(BaseModel):
    tag: str

class TagCreate(TagBase):
    pass

class TagOut(TagBase):
    id: int

    model_config = {
        "from_attributes": True
    }
