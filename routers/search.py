from fastapi import APIRouter, Depends, Query
from schemas import SearchOut
from database import get_db
from services import get_user_gifs_with_tags
from typing import Optional, List

router = APIRouter()


@router.get('/search', response_model=SearchOut)
def search_gifs(
        tg_user_id: int = Query(),
        tags: Optional[List[str]] = Query(None),
        db=Depends(get_db)):
    return get_user_gifs_with_tags(db, tg_id=tg_user_id, tags=tags)
