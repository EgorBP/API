from fastapi import APIRouter, Depends, Query, UploadFile, Form, status, Body

from app.api.dependencies.auth import get_user_id_from_jwt
from app.api.dependencies.service import get_user_library_service, get_user_service
from app.api.dependencies.validation import validate_gif_file
from app.schemas.common import CursorPaginatedResponse
from app.schemas.gif import GifOut
from app.schemas.tag import RawTagsOut, TagString
from app.schemas.user import UserOut
from app.services import UserLibraryService
from app.services.user import UserService

router = APIRouter()


@router.get(
    '',
    response_model=UserOut,
    summary="Get the authenticated user's info",
)
async def get_user_info(
        user_id: int = Depends(get_user_id_from_jwt),
        user_service: UserService = Depends(get_user_service)
):
    """Returns the authenticated user's public info."""
    return await user_service.get_user_info(
        user_id=user_id
    )


@router.get(
    '/gifs/count',
    response_model=int,
    summary="Get the authenticated user's GIF count",
)
async def get_user_gifs_count(
        user_id: int = Depends(get_user_id_from_jwt),
        user_library_service: UserLibraryService = Depends(get_user_library_service)
):
    """Returns the number of GIFs in the authenticated user's library."""
    return await user_library_service.get_user_gifs_count(
        user_id=user_id
    )


@router.get(
    '/gifs',
    response_model=CursorPaginatedResponse[GifOut, int],
    summary="List the authenticated user's GIFs",
)
async def get_user_gifs(
        gif_ids: list[int] | None = Query(None),
        tags: set[str] | None = Query(None),
        cursor: int | None = Query(None),
        limit: int = Query(default=20, ge=1, le=100),
        user_id: int = Depends(get_user_id_from_jwt),
        user_library_service: UserLibraryService = Depends(get_user_library_service)
):
    """Lists the authenticated user's GIFs, each including its tags.

    ### Features:
    - Filter by specific `gif_ids`.
    - Filter by `tags` — a GIF is only returned if it has **all** of the
      given tags, not just any of them.
    - Cursor-based pagination via `cursor` and `limit`.

    ### Notes:
    - `limit` is capped between **1 and 100**.
    """
    return await user_library_service.get_user_gifs_with_tags(
        user_id=user_id,
        gif_ids=gif_ids,
        tags=tags,
        cursor=cursor,
        limit=limit
    )


@router.get(
    '/tags/all', 
    response_model=RawTagsOut,
    summary="List all of the authenticated user's tags",
)
async def get_user_tags(
        user_id: int = Depends(get_user_id_from_jwt),
        user_library_service: UserLibraryService = Depends(get_user_library_service)
):
    """Returns every distinct tag the authenticated user has used across their GIFs.

    ### Notes:
    - Returns an empty list if the user has no tagged GIFs, rather than
      a 404.
    """
    return await user_library_service.get_all_user_tags(user_id=user_id)


@router.post(
    '/gifs/new',
    response_model=GifOut,
    summary="Upload a new GIF",
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "description": "File is not a valid GIF/MP4, or its content doesn't match its declared type.",
        },
    },
)
async def upload_new_gif(
        file: UploadFile = Depends(validate_gif_file),
        tags: set[TagString] = Form(min_length=1),
        user_id: int = Depends(get_user_id_from_jwt),
        user_library_service: UserLibraryService = Depends(get_user_library_service)
):
    """Uploads a new GIF/MP4 and adds it to the authenticated user's library.

    ### Features:
    - Automatically deduplicates by file content hash — if an identical
      file was already uploaded by any user, it's reused instead of
      being stored again.
    - Only `image/gif` and `video/mp4` are accepted, verified by both
      MIME type and file header.

    ### Notes:
    - At least one tag is required (`min_length=1`).
    - `tags` is submitted as multipart form data, not JSON.
    """
    return await user_library_service.add_new_user_gif(
        user_id=user_id,
        gif_file=file,
        tags=tags
    )


@router.put(
    '/gifs/{gif_id}/tags', 
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Replace tags on one of the authenticated user's GIFs",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "No GIF exists with the given `gif_id`.",
        },
    },
)
async def update_gif_tags(
        gif_id: int,
        tags: set[TagString] = Body(min_length=1),
        user_id: int = Depends(get_user_id_from_jwt),
        user_library_service: UserLibraryService = Depends(get_user_library_service)
):
    """Replaces the authenticated user's complete tag set on one of their GIFs.

    ### Notes:
    - `tags` is treated as the **full replacement set** — tags not
      included are removed, new ones are created if needed.
    - At least one tag is required (`min_length=1`).
    """
    await user_library_service.set_new_user_tags_on_gif(
        user_id=user_id,
        gif_id=gif_id,
        tags=tags
    )


@router.delete(
    '/gifs', 
    response_model=int,
    summary="Remove GIFs from the authenticated user's library",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "None of the given `gif_ids` were linked to this user.",
        },
    },
)
async def delete_user_gif(
        gif_ids: list[int] = Query(),
        user_id: int = Depends(get_user_id_from_jwt),
        user_library_service: UserLibraryService = Depends(get_user_library_service)
):
    """Removes GIFs from the authenticated user's library.

    ### Notes:
    - Only unlinks the GIFs from this user — the underlying files and
      database rows are **left untouched**, since other users may still
      have them in their libraries.
    """
    return await user_library_service.unlink_user_from_gif(
        user_id=user_id,
        gif_ids=gif_ids
    )


@router.delete(
    '',
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete the authenticated user's account",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "No user exists with this ID (already deleted).",
        },
    },
)
async def delete_user(
        user_id: int = Depends(get_user_id_from_jwt),
        user_service: UserService = Depends(get_user_service)
):
    """Deletes the authenticated user's account.

    ### Notes:
    - All of the user's GIF/tag links are removed automatically via
      cascading delete — the underlying GIF files remain, since other
      users may still reference them.
    """
    return await user_service.delete_user(
        user_id=user_id
    )
