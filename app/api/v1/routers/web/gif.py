from fastapi import APIRouter, Depends, Query, UploadFile, Form, status

from app.api.dependencies.service import get_gif_service
from app.schemas.gif import PopularGifsOut
from app.services.gif import GifService

router = APIRouter()


@router.get(
    '/popular',
    response_model=PopularGifsOut
)
async def get_user_info(
        gif_service: GifService = Depends(get_gif_service)
):
    return await gif_service.get_popular()
