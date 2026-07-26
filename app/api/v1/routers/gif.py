from fastapi import APIRouter, Depends, Query

from app.api.dependencies.service import get_gif_service, get_tag_service
from app.schemas.common import CursorPaginatedResponse, SortOrder
from app.schemas.gif import PopularGifsOut, RawGifOut
from app.schemas.tag import RawTagsOut, TagString
from app.services.gif import GifService
from app.services.tag import TagService

router = APIRouter()


@router.get(
    '/popular',
    response_model=PopularGifsOut,
    summary="Get site-wide popular GIFs",
)
async def get_popular_gifs(
        gif_service: GifService = Depends(get_gif_service)
):
    """Returns the cached list of the most popular GIFs across all users.

    ### Notes:
    - Backed entirely by a Redis cache, refreshed periodically by a
      background task — **never queries the database directly**.
    - Returns an empty list if the cache hasn't been populated yet.
    """
    return await gif_service.get_popular()


@router.get(
    '',
    response_model=CursorPaginatedResponse[RawGifOut, int],
    summary="Search GIFs across all users",
)
async def get_gifs(
        sorting: SortOrder = Query(default=SortOrder.DESC),
        tags: set[str] | None = Query(None),
        cursor: int | None = Query(None),
        limit: int = Query(default=20, ge=1, le=100),
        gif_service: GifService = Depends(get_gif_service)
):
    """Lists GIFs across all users, optionally filtered by tags.

    ### Features:
    - Filter by `tags` — a GIF is returned if **any** user has tagged it
      with **all** of the given tags.
    - Sort ascending or descending by GIF ID, with cursor-based
      pagination via `cursor` and `limit`.

    ### Notes:
    - Only the first page of untagged or single-tag queries is served
      from cache; everything else queries the database directly.
    - `limit` is capped between **1 and 100**.
    """
    return await gif_service.get_gifs(
        sorting=sorting,
        tags=tags,
        cursor=cursor,
        limit=limit        
    )


@router.get(
    '/{gif_id}/popular/tags',
    response_model=RawTagsOut,
    summary="Get the most popular tags for a specific GIF",
)
async def get_popular_tags_for_gif(
        gif_id: int,
        limit: int = Query(default=5, ge=1, le=10),
        tag_service: TagService = Depends(get_tag_service)
):
    """Returns the most-used tags for a GIF, across all users who tagged it.

    - **gif_id**: Internal ID of the GIF.
    - **limit**: Maximum number of tags to return (1–10).

    ### Notes:
    - Does not verify that `gif_id` actually exists — an unknown ID
      simply returns an empty list rather than a 404.
    """
    return await tag_service.get_popular_tags_for_gif(
        gif_id=gif_id,
        limit=limit        
    )
