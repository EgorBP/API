from fastapi import APIRouter, Depends, Query
from schemas import GifOut, GifUpdate, Successful
from database import get_db
from services import get_user_gifs_with_tags, set_new_user_tags_on_gif
from crud import delete_instances, get_instances
from models import UserGifTag, User, Gif


router = APIRouter(
    prefix='/user'
)


@router.get('/{tg_user_id}/gif/{tg_gif_id}', response_model=GifOut)
def search_gifs(
        tg_user_id: int,
        tg_gif_id: str,
        db=Depends(get_db)):
    return get_user_gifs_with_tags(db, tg_id=tg_user_id, tg_gifs_id=tg_gif_id)['gifs_data'][0]


@router.put('/{tg_user_id}/gif/{tg_gif_id}', response_model=Successful)
def search_gifs(
        tg_user_id: int,
        tg_gif_id: str,
        gif_data: GifUpdate,
        db=Depends(get_db)):
    set_new_user_tags_on_gif(db, tg_user_id, tg_gif_id, gif_data.tags)
    # return get_user_gifs_with_tags(db, tg_id=tg_user_id, tg_gifs_id=tg_gif_id)['gifs_data'][0]
    return Successful()


@router.delete('/{tg_user_id}/gif/{gif_id}', response_model=Successful)
def search_gifs(
        tg_user_id: int,
        tg_gif_id: str,
        db=Depends(get_db)):
    delete_instances(db, UserGifTag, filters={
        UserGifTag.user_id: get_instances(db, User, columns=User.id, filters={User.tg_id: tg_user_id})[0][0],
        UserGifTag.gif_id: get_instances(db, Gif, columns=Gif.id, filters={Gif.tg_gif_id: tg_gif_id})[0][0],
    })
    return Successful()
