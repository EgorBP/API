from typing import Final
from sqlalchemy import select, func, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import _BaseRepository
from app.models import User, UserGifTag


class UserRepository(_BaseRepository[User]):
    """CRUD operations for the `User` model.

    Only `create_user` and read helpers specific to users are added here;
    generic get/update operations are inherited from `_BaseRepository`.
    """
    _model: Final = User

    def __init__(
            self, 
            session: AsyncSession
    ):
        """Initializes the repository.

        Args:
            session: The async SQLAlchemy session to execute queries on.
        """
        super().__init__(session)

    async def create_user(
            self,
            tg_id: int,
    ) -> _model:
        """Creates a user, or returns the existing one if already registered.

        Thin wrapper around `create_one`. If a `User` row with this
        `tg_id` already exists (unique constraint), the conflict is
        resolved by returning the existing row rather than raising.

        Args:
            tg_id: Telegram ID of the user.

        Returns:
            The inserted or already-existing `User` row.
        """
        return await self.create_one({
            User.tg_id: tg_id
        })
    
    async def delete_user(
            self,
            user_id: int
    ) -> _model | None:
        """Deletes a user by internal ID.

        Related `UserGifTag` rows are removed automatically via the
        database's `ON DELETE CASCADE`.

        Args:
            user_id: Internal ID of the user to delete.

        Returns:
            The deleted `User` row, or None if no user with this ID
            existed.
        """
        user= await self.delete_many(
            filters={self._model.id: user_id}
        )
        
        return user[0] if user else None
    
    async def get_user_gifs_count(
            self,
            user_id: int
    ) -> int:
        """Counts how many distinct GIFs a user has in their library.

        Counts distinct `Gif.id` values referenced by the user's
        `UserGifTag` rows, so a GIF tagged with several tags is still
        counted once.

        Args:
            user_id: Internal ID of the user.

        Returns:
            The number of distinct GIFs in the user's library, or 0 if
            none.
        """
        stmt = (
            select(func.count(distinct(UserGifTag.gif_id)))
            .select_from(UserGifTag)
            .where(UserGifTag.user_id == user_id)
        )
        
        return await self._session.scalar(stmt) or 0
