from pydantic import BaseModel


# ===== Пользователь =====
class UserBase(BaseModel):
    tg_id: int

class UserCreate(UserBase):
    pass

class UserOut(UserBase):
    id: int

    model_config = {
        "from_attributes": True
    }


# ===== Гифка =====
class GifBase(BaseModel):
    tg_gif_id: str

class GifCreate(GifBase):
    pass

class GifOut(GifBase):
    id: int
    tags: list[str]

    model_config = {
        "from_attributes": True
    }


# ===== Поиск по тегам =====
class SearchBase(BaseModel):
    tg_user_id: int
    tags: list[str]

class SearchOut(UserOut):
    gifs_data: list[GifOut]


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


# ===== Связь юзер-гифка-тег =====
class UserGifTagBase(BaseModel):
    user_id: int
    gif_id: int
    tag_id: int
