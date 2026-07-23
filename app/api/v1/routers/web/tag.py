from fastapi import APIRouter, Depends, Query, UploadFile, Form, status

from app.api.dependencies.service import get_tag_service 
from app.schemas.tag import PopularTagsOut
from app.services.tag import TagService

router = APIRouter()


@router.get(
    '/popular',
    response_model=PopularTagsOut
)
async def get_popular(
        tag_service: TagService = Depends(get_tag_service)
):
    return await tag_service.get_popular()
