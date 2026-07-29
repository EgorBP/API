from collections.abc import Sequence
from typing import Final

from sqlalchemy import Row, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Gif, Tag, UserGifTag
from app.repositories import _BaseRepository
from app.schemas.common import SortOrder


class GifRepository(_BaseRepository[Gif]):
    """CRUD operations for the `Gif` model.

    Only `create_gif` and read helpers specific to GIFs are added here;
    generic get/update/delete operations are inherited from
    `_BaseRepository`.
    """
    _model: Final = Gif

    def __init__(
            self, 
            session: AsyncSession
    ):
        """Initializes the repository.

        Args:
            session: The async SQLAlchemy session to execute queries on.
        """
        super().__init__(session)

    async def create_gif(
            self,
            file_path: str,
            file_hash: str
    ) -> _model:
        """Creates a `Gif` row for a file already saved to storage.

        Thin wrapper around `create_one` that maps the two required
        columns of the `Gif` model.

        Args:
            file_path: Path to the file, relative to `settings.BASE_DIR`.
            file_hash: SHA-256 hash of the file contents.

        Returns:
            The inserted `Gif` row.

        Raises:
            IntegrityError: If `file_path` or `file_hash` already exists
                (both are unique columns).
        """
        return await self.create_one({
            Gif.file_path: file_path,
            Gif.file_hash: file_hash
        })

    async def get_popular_gifs(
            self,
            limit: int
    ) -> list[Row[tuple[int, str]]]:
        """Fetches the most-saved GIFs across all users.

        Popularity is measured by how many `UserGifTag` rows reference
        each GIF (i.e. how many users have it tagged in their library),
        regardless of which tags were used. GIFs with zero saves are
        included via an outer join and sorted last.

        Args:
            limit: Maximum number of GIFs to return.

        Returns:
            Rows of `(Gif.id, Gif.file_path)`, ordered by save count
            descending, then by `Gif.id` descending as a tiebreaker.
        """
        stmt = (
            select(
                Gif.id,
                Gif.file_path,
            )
            .select_from(Gif)
            .outerjoin(UserGifTag, UserGifTag.gif_id == Gif.id)
            .group_by(Gif.id, Gif.file_path)
            .order_by(
                func.count(UserGifTag.user_id).desc(),
                Gif.id.desc()
            )
            .limit(limit)
        )

        result = await self._session.execute(stmt)
        return list(result.all())

    async def search_user_gifs_with_tags(
            self,
            user_id: int,
            gif_ids: Sequence[int] | None = None,
            tags: set[str] | None = None,
            cursor: int | None = None,
            limit: int | None = None
    ) -> list[Row[tuple]]:
        """Searches a user's own GIFs, with each row aggregating all its tags.

        Only GIFs the user has tagged at least once are returned. If
        `tags` is given, a GIF is included only if it has **all** of the
        given tags (not just any of them). Results are always ordered by
        `Gif.id` descending; `cursor` continues from a previous page by
        excluding IDs greater than or equal to it.

        Args:
            user_id: Internal ID of the user whose GIFs to search.
            gif_ids: If given, restricts the search to these GIF IDs.
            tags: If given, only GIFs tagged with all of these tags (by
                this user) are returned.
            cursor: If given, only returns GIFs with `id` strictly less
                than this value, for keyset pagination.
            limit: Maximum number of rows to return.

        Returns:
            Rows of `(Gif.id, Gif.file_path, tags)`, where `tags` is the
            array of every tag the user has attached to that GIF.

        Example:
            Fetching the next page of a user's GIFs tagged both "cat" and
            "funny", continuing after GIF id 105::

                rows = await gif_repo.search_user_gifs_with_tags(
                    user_id=42, tags={"cat", "funny"}, cursor=105, limit=20
                )
        """
        stmt = (
            select(
                Gif.id,
                Gif.file_path,
                func.array_agg(Tag.tag).label("tags")
            )
            .select_from(UserGifTag)
            .join(Gif, UserGifTag.gif_id == Gif.id)
            .join(Tag, UserGifTag.tag_id == Tag.id)
            .order_by(Gif.id.desc())
            .where(UserGifTag.user_id == user_id)
            .group_by(
                Gif.id,
                Gif.file_path
            )
        )

        if gif_ids:
            stmt = stmt.where(Gif.id.in_(gif_ids))

        if tags:
            stmt = stmt.having(
                func.count(distinct(Tag.tag))
                .filter(Tag.tag.in_(tags)) == len(tags)
            )

        if cursor:
            stmt = stmt.where(Gif.id < cursor)

        if limit:
            stmt = stmt.limit(limit)

        result = await self._session.execute(stmt)
        return list(result.all())
    
    async def search_gifs_by_tags(
            self,
            tags: set[str] | None = None,
            sorting: SortOrder = SortOrder.DESC,
            cursor: int | None = None,
            limit: int | None = None
    ) -> list[Row[tuple[int, str]]]:
        """Searches all GIFs across users, optionally filtered by tags.

        Unlike `search_user_gifs_with_tags`, this is not scoped to a
        single user — it matches a GIF if **any** user has tagged it with
        **all** of the given tags. If `tags` is empty or None, all GIFs
        are returned.

        Args:
            tags: If given, only GIFs tagged with all of these tags (by
                any user) are returned.
            sorting: Sort direction by `Gif.id`. Also determines which
                side of `cursor` is used for pagination.
            cursor: If given, excludes GIFs on the far side of this ID
                relative to `sorting` (`< cursor` for DESC, `> cursor` for
                ASC), for keyset pagination.
            limit: Maximum number of rows to return.

        Returns:
            Rows of `(Gif.id, Gif.file_path)`, ordered by `Gif.id`
            according to `sorting`.

        Example:
            Fetching the next page of untagged-filtered results, oldest
            first, continuing after GIF id 10::

                rows = await gif_repo.search_gifs_by_tags(
                    sorting=SortOrder.ASC, cursor=10, limit=20
                )
        """
        stmt = (
            select(
                Gif.id,
                Gif.file_path,
            )
            .select_from(Gif)
        )
        
        if tags:
            stmt = (
                stmt
                .join(UserGifTag, UserGifTag.gif_id == Gif.id)
                .join(Tag, UserGifTag.tag_id == Tag.id)
                .where(Tag.tag.in_(tags))
                .group_by(Gif.id, Gif.file_path)
                .having(func.count(distinct(Tag.id)) == len(tags))
            )

        if sorting == SortOrder.DESC:
            stmt = stmt.order_by(Gif.id.desc())
        else:
            stmt = stmt.order_by(Gif.id.asc())

        if cursor:
            if sorting == SortOrder.DESC:
                stmt = stmt.where(Gif.id < cursor)
            else:
                stmt = stmt.where(Gif.id > cursor)
            
        if limit:
            stmt = stmt.limit(limit)

        result = await self._session.execute(stmt)
        return list(result.all())
