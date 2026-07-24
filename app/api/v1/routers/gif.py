from fastapi import APIRouter, Depends, Query

from app.api.dependencies.service import get_gif_service, get_tag_service
from app.schemas.common import CursorPaginatedResponse, SortOrder
from app.schemas.gif import PopularGifsOut, RawGifOut
from app.schemas.tag import RawTagsOut
from app.services.gif import GifService
from app.services.tag import TagService

router = APIRouter()


@router.get(
    '/popular',
    response_model=PopularGifsOut
)
async def get_popular_gifs(
        gif_service: GifService = Depends(get_gif_service)
):
    return await gif_service.get_popular()


@router.get(
    '',
    response_model=CursorPaginatedResponse[RawGifOut, int]
)
async def get_gifs(
        sorting: SortOrder = Query(default=SortOrder.DESC),
        tags: set[str] | None = Query(None),
        cursor: int | None = Query(None),
        limit: int = Query(default=20, ge=1, le=100),
        gif_service: GifService = Depends(get_gif_service)
):
    return await gif_service.get_gifs(
        sorting=sorting,
        tags=tags,
        cursor=cursor,
        limit=limit        
    )


@router.get(
    '/{gif_id}/popular/tags',
    response_model=RawTagsOut
)
async def get_popular_tags_for_gif(
        gif_id: int,
        limit: int = Query(default=5, ge=1, le=10),
        tag_service: TagService = Depends(get_tag_service)
):
    return await tag_service.get_popular_tags_for_gif(
        gif_id=gif_id,
        limit=limit        
    )
