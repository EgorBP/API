from typing import Final

from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Tag, UserGifTag
from app.repositories import _BaseRepository


class TagRepository(_BaseRepository[Tag]):
    """CRUD operations for the `Tag` model.

    Only `create_tag`, `fake_upsert_tags`, and read helpers specific to
    tags are added here; generic get/update/delete operations are
    inherited from `_BaseRepository`.
    """
    _model: Final = Tag

    def __init__(
            self, 
            session: AsyncSession
    ):
        """Initializes the repository.

        Args:
            session: The async SQLAlchemy session to execute queries on.
        """
        super().__init__(session)

    async def create_tag(
            self,
            tag: str,
    ) -> _model:
        """Creates a tag, or returns the existing one if it already exists.

        Thin wrapper around `create_one`. If a `Tag` row with this exact
        text already exists (unique constraint on `Tag.tag`), the
        conflict is resolved by returning the existing row rather than
        raising.

        Args:
            tag: The tag's text value.

        Returns:
            The inserted or already-existing `Tag` row.
        """
        return await self.create_one({
            Tag.tag: tag
        })
    
    async def fake_upsert_tags(
            self,
            tags: set[str]
    ) -> list[_model]:
        """Ensures every given tag exists, creating missing ones.

        Called "fake" upsert because on conflict it does not change any
        data (`set_={"tag": Tag.tag}` is a no-op update) — its only
        purpose is to make ``RETURNING`` also include rows that already
        existed, so the full set of `Tag` rows (new and pre-existing) is
        always returned in a single round trip.

        Args:
            tags: The tag text values to ensure exist.

        Returns:
            The `Tag` rows for every value in `tags`, whether newly
            created or already present. Order is not guaranteed.

        Example:
            Making sure a GIF's new tag set all exist as rows before
            linking them to the GIF::

                tag_rows = await tag_repo.fake_upsert_tags({"cat", "funny"})
                tag_ids = {t.id for t in tag_rows}
        """
        stmt = (
            insert(Tag)
            .values([{"tag": tag} for tag in tags])
            .on_conflict_do_update(
                index_elements=[Tag.tag],
                set_={"tag": Tag.tag},
            )
            .returning(self._model)
        )
        
        result = await self._session.scalars(stmt)
        return list(result)

    async def get_unique_user_tags(
            self,
            user_id: int,
    ) -> list[str]:
        """Fetches every distinct tag a user has used across their GIFs.

        Args:
            user_id: Internal ID of the user.

        Returns:
            The distinct tag values the user has attached to any GIF.
            Empty if the user has no tagged GIFs.
        """
        stmt = (
            select(Tag.tag)
            .distinct()
            .select_from(UserGifTag)
            .join(Tag, UserGifTag.tag_id == Tag.id)
            .where(UserGifTag.user_id == user_id)
        )

        return list(await self._session.scalars(stmt))

    async def get_popular_tags(
            self,
            limit: int
    ) -> list[str]:
        """Fetches the most-used tags across all users and GIFs.

        Popularity is measured by how many `UserGifTag` rows use each tag,
        i.e. how many times it has been applied in total.

        Args:
            limit: Maximum number of tags to return.

        Returns:
            Tag values ordered by usage count descending.
        """
        stmt = (
            select(
                Tag.tag
            )
            .select_from(Tag)
            .join(UserGifTag, UserGifTag.tag_id == Tag.id)
            .group_by(Tag.tag)
            .order_by(
                func.count(UserGifTag.user_id).desc()
            )
            .limit(limit)
        )

        result = await self._session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_popular_gif_tags(
            self,
            gif_id: int,
            limit: int
    ) -> list[str]:
        """Fetches the most-used tags for a single GIF, across all users.

        Popularity is measured by how many users have applied each tag to
        this specific GIF.

        Args:
            gif_id: Internal ID of the GIF.
            limit: Maximum number of tags to return.

        Returns:
            Tag values ordered by usage count descending, scoped to
            `gif_id`.
        """
        stmt = (
            select(Tag.tag)
            .select_from(UserGifTag)
            .join(Tag, UserGifTag.tag_id == Tag.id)
            .where(UserGifTag.gif_id == gif_id)
            .group_by(Tag.tag)
            .order_by(func.count(UserGifTag.user_id).desc())
            .limit(limit)
        )
        
        tags = await self._session.scalars(stmt)
        return list(tags)
