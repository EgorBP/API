from fastapi import APIRouter, Depends, Query, HTTPException
from app.schemas import SearchOut
from app.database import get_db
from app.services import get_user_gifs_with_tags
from typing import Optional, List


router = APIRouter()


@router.get('/search', response_model=SearchOut)
def search_gifs(
        tg_user_id: int = Query(),
        tags: Optional[List[str]] = Query(None),
        db=Depends(get_db)
):
    """
    Поиск GIF по тегам для конкретного пользователя.

    - **tg_user_id**: Telegram ID пользователя
    - **tags**: список тегов для фильтрации (опционально).
      Если не передан, вернутся все GIF пользователя.

    **Returns:**
    Объект `SearchOut` с полями:
    - **id**: int — внутренний ID пользователя в базе
    - **tg_id**: int — Telegram ID пользователя
    - **gifs_data**: список объектов `GifOut`, где каждый содержит:
        - **id**: int — внутренний ID GIF
        - **tg_gif_id**: str — идентификатор GIF в Telegram
        - **tags**: list[str] — список тегов, связанных с GIF
    """
    data = get_user_gifs_with_tags(db, tg_user_id=tg_user_id, tags=tags)
    if not data:
        raise HTTPException(status_code=404, detail="User not found")
    
    return data
