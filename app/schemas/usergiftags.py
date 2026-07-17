from pydantic import BaseModel


# ===== Связь юзер-гифка-тег =====
class UserGifTagBase(BaseModel):
    user_id: int
    gif_id: int
    tag_id: int
