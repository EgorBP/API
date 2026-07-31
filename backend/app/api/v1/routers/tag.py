from fastapi import APIRouter, Depends

from app.api.dependencies.service import get_tag_service
from app.schemas.tag import PopularTagsOut
from app.services.tag import TagService

router = APIRouter()


@router.get(
    '/popular',
    response_model=PopularTagsOut,
    summary="Get site-wide popular tags",
)
async def get_popular(
        tag_service: TagService = Depends(get_tag_service)
):
    """Returns the cached list of the most popular tags across all users.

    ### Notes:
    - Backed entirely by a Redis cache, refreshed periodically by a
      background task — **never queries the database directly**.
    - Returns an empty list if the cache hasn't been populated yet.
    """
    return await tag_service.get_popular()
