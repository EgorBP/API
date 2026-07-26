"""Shared test-only constants and data-seeding helpers used across the suite.

Kept separate from `conftest.py` so plain functions/constants can be
imported directly (`from tests.helpers import GIF_BYTES`) without going
through pytest's fixture injection, while `conftest.py` still exposes a
`seed_gif` fixture bound to the current test's `db_session` for the common
case.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Gif
from app.repositories.gif import GifRepository
from app.repositories.tag import TagRepository
from app.repositories.user import UserRepository
from app.repositories.user_gif_tag import UserGifTagRepository

# Minimal byte sequences that pass the upload endpoint's MIME/content-sniffing
# validation for GIF and MP4 files, without needing a real media file on disk.
GIF_BYTES = b"GIF89a" + b"\x00" * 20
MP4_BYTES = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 20


async def seed_gif_with_tags(
    db_session: AsyncSession, *, tg_id: int, file_hash: str, tags: set[str]
) -> Gif:
    """Creates a user, a GIF, and links them through the given tags.

    Bypasses the API/service layers to set up a GIF that's already sitting
    in some user's library, for tests that only care about what happens
    *after* that GIF exists (searching, caching, deleting, ...). Prefer the
    `seed_gif` fixture in `conftest.py` in tests, which is already bound to
    the current `db_session`.
    """
    user = await UserRepository(db_session).create_user(tg_id=tg_id)
    gif = await GifRepository(db_session).create_gif(file_path=f"{file_hash}.gif", file_hash=file_hash)
    tag_rows = await TagRepository(db_session).fake_upsert_tags(tags)

    ugt_repo = UserGifTagRepository(db_session)
    for tag in tag_rows:
        await ugt_repo.create_user_gif_tag(user_id=user.id, gif_id=gif.id, tag_id=tag.id)

    return gif
