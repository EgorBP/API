from fastapi import UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Sequence
from redis.asyncio import Redis
import json
import logging

from app.core.exceptions import GifNotFoundError, TagNotFoundError
from app.models import UserGifTag, Gif, Tag
from app.schemas.common import CursorPaginatedResponse, CursorPaginationMeta
from app.schemas.gif import GifOut
from app.repositories import UserGifTagRepository, TagRepository, GifRepository, UserRepository
from app.schemas.tag import RawTagsOut
from app.services.interface import StorageProvider
from app.services.user import UserService
from app.utils.redis import invalidate_many
from app.utils.storage import create_unique_filename_and_hash

logger = logging.getLogger(__name__)


# TODO: update dockstring
class UserLibraryService:
    def __init__(
            self,
            session: AsyncSession,
            redis: Redis,
            storage: StorageProvider,
    ):
        self.storage = storage
        
        self._session = session
        self._redis = redis
        
        self._base_cache_ttl = 300
        
    async def get_user_gifs_count(
            self,
            user_id: int
    ):
        cache_path = f"{self._get_service_cache_prefix(user_id)}:gifs:count"
        gifs_count = await self._redis.get(cache_path)
        if gifs_count:
            logger.info(
                "Get user gifs count",
                extra={
                    "user_id": user_id,
                    "source": "cache"
                }
            )
            return gifs_count
        
        user_repo = UserRepository(self._session)
        gifs_count = await user_repo.get_user_gifs_count(user_id)
        logger.info(
            "Get user gifs count",
            extra={
                "user_id": user_id,
                "source": "database"
            }
        )
        
        await self._redis.set(cache_path, gifs_count, ex=self._base_cache_ttl)
        logger.debug(
            f"Set user gifs count in cache for {self._base_cache_ttl}",
            extra={
                "user_id": user_id,
            }
        )
        
        return gifs_count

    async def get_user_gifs_with_tags(
            self,
            user_id: int,
            limit: int,
            gif_ids: Sequence[int] | int | None  = None,
            tags: set[str] | str | None = None,
            cursor: int | None = None
    ) -> CursorPaginatedResponse:
        gif_repo = GifRepository(self._session)
        
        if isinstance(gif_ids, int):
            gif_ids = (gif_ids,)
    
        if isinstance(tags, str):
            tags = {tags}

        # Кеширование
        tags = tags or set()
        normalized_tags = sorted([tag.strip() for tag in tags])
        tags_string = ",".join(normalized_tags) if normalized_tags else "all"
        gif_ids_c = gif_ids or []
        normalized_gif_ids = sorted([str(gif_id).strip() for gif_id in gif_ids_c])
        gif_ids_string = ",".join(normalized_gif_ids) if normalized_gif_ids else "all"

        cursor_string = str(cursor) if cursor is not None else "first_page"
        cache_key = f"{self._get_service_cache_prefix(user_id)}:gif_ids:{gif_ids_string}:tags:{tags_string}:cursor:{cursor_string}:limit:{limit}"
    
        cached_data = await self._redis.get(cache_key)
        if cached_data:
            logger.info(
                "Get user gifs with tags from cache",
                extra={
                    "source": "database",
                    "user_id": user_id,
                }
            )
            return CursorPaginatedResponse.model_validate_json(cached_data)
        
        rows = await gif_repo.search_user_gifs_with_tags(
            user_id=user_id,
            gif_ids=gif_ids,
            tags=tags,
            cursor=cursor,
            limit=limit + 1
        )
        
        has_next = len(rows) > limit

        if has_next:
            rows = rows[:limit]
            next_cursor = rows[-1].id
        else:
            next_cursor = None
        
        gifs_data = [
            GifOut.model_validate(row._mapping)
            for row in rows
        ]
        
        final_data = CursorPaginatedResponse[GifOut, int](
            data=gifs_data,
            pagination=CursorPaginationMeta[int](
                limit=limit,
                has_next=has_next,
                next_cursor=next_cursor,
            )
        )
        
        await self._redis.set(cache_key, final_data.model_dump_json(), ex=self._base_cache_ttl)
        
        logger.debug(
            f"Set new cache for {self._base_cache_ttl}s",
            extra={
                "user_id": user_id,
            }
        )
        logger.info(
            "Get user gifs with tags from database",
            extra={
                "source": "database",
                "user_id": user_id,
            }
        )
    
        return final_data
    
    async def get_all_user_tags(
            self,
            user_id: int,
    ) -> RawTagsOut:
        tag_repo = TagRepository(self._session)

        cache_key = f"{self._get_service_cache_prefix(user_id)}:all_user_tags"
        
        cached_data = await self._redis.get(cache_key)
        if cached_data:
            logger.info(
                "Get all user tags from cache",
                extra={
                    "source": "cache",
                    "user_id": user_id,
                }
            )
            return RawTagsOut.model_validate_json(cached_data)
        
        tags = await tag_repo.get_unique_user_tags(user_id)
        
        tags = RawTagsOut(
            tags=tags,
            count=len(tags)
        )
        
        await self._redis.set(cache_key, tags.model_dump_json(), ex=self._base_cache_ttl)
    
        logger.info(
            f"Set new cache for {self._base_cache_ttl}s",
            extra={
                "user_id": user_id,
            }
        )
        logger.info(
            "Get all user tags from database",
            extra={
                "source": "database",
                "user_id": user_id,
            }
        )
        
        return tags
    
    async def add_new_user_gif(
            self,
            user_id: int,
            gif_file: UploadFile,
            tags: set[str]
    ) -> GifOut:
        tag_repository = TagRepository(self._session)
        gif_repository = GifRepository(self._session)
        user_gif_tag_repository = UserGifTagRepository(self._session)
        
        filename, file_hash = await create_unique_filename_and_hash(gif_file)
        
        gif = await gif_repository.get_one_orm(
            filters={Gif.file_hash: file_hash}
        )
        
        try:
            log_msg = "Set new tags for exist user GIF"
            if gif is None:
                file_path = await self.storage.save_file(gif_file, filename)
                gif = await gif_repository.create_gif(
                    file_path=file_path,
                    file_hash=file_hash
                )
                
                log_msg = "Create new GIF and set tags"

            gif_id = gif.id
            await self._set_new_user_tags_on_gif_internal(
                user_id=user_id,
                gif_id=gif_id,
                tags=tags,
                tag_repository=tag_repository,
                user_gif_tag_repository=user_gif_tag_repository
            )

            await self._session.commit()

            logger.info(
                log_msg,
                extra={
                    "user_id": user_id,
                    "gif_id": gif.id
                }
            )

            await self._invalidate_current_service_cache(user_id)
            
            return GifOut(
                id=gif_id,
                file_path=gif.file_path,
                tags=tags
            )
        
        except Exception:
            await self._session.rollback()
            logger.exception(
                "Error when create new GIF or set tags",
                extra={
                    "user_id": user_id,
                }
            )
            raise

    async def set_new_user_tags_on_gif(
            self,
            user_id: int,
            gif_id: int,
            tags: set[str],
    ) -> None:
        tag_repository = TagRepository(self._session)
        user_gif_tag_repository = UserGifTagRepository(self._session)
        gif_repository = GifRepository(self._session)
        
        if await gif_repository.get_one(
                columns=Gif.id,
                filters={Gif.id: gif_id}
        ):
            try:
                await self._set_new_user_tags_on_gif_internal(
                    user_id=user_id,
                    gif_id=gif_id,
                    tags=tags,
                    tag_repository=tag_repository,
                    user_gif_tag_repository=user_gif_tag_repository
                )
                
                await self._session.commit()
                logger.info(
                    "User GIF tags updated",
                    extra={
                        "user_id": user_id,
                        "gif_id": gif_id
                    }
                )

                # Инвалидируем кэш
                await self._invalidate_current_service_cache(user_id)

            except Exception:
                await self._session.rollback()
                logger.exception(
                    "Error when update tags for user GIF",
                    extra={
                        "user_id": user_id,
                        "gif_id": gif_id
                    }
                )
                raise
        else:
            raise GifNotFoundError(
                gif_id=gif_id,
                user_id=user_id
            )
    
    async def unlink_user_from_gif(
            self,
            user_id: int,
            gif_ids: list[int],
    ) -> int:
        user_gif_tag_repository = UserGifTagRepository(self._session)
        
        try:
            deleted = await user_gif_tag_repository.delete_many(
                filters={
                    UserGifTag.user_id: user_id,
                    UserGifTag.gif_id: gif_ids,
                }
            )
            if deleted is None:
                raise GifNotFoundError(
                    user_id=user_id
                )
            
            await self._session.commit()
            logger.info(
                f"{len(deleted)} user GIFs deleted",
                extra={
                    "user_id": user_id,
                }
            )
            
            await self._invalidate_current_service_cache(user_id)  
                
            return len(deleted)
        
        except Exception:
            await self._session.rollback()
            logger.exception(
                "Error when delete user GIF and tags",
                extra={
                    "user_id": user_id,
                }
            )
            raise

    async def _invalidate_current_service_cache(
            self,
            user_id: int
    ):
        objects_count = await invalidate_many(
            redis=self._redis,
            match=f"{self._get_service_cache_prefix(user_id)}:*"
        )
        
        logger.debug(
            f"User library cache ({objects_count} elements) invalidated",
            extra={
                "user_id": user_id,
            }
        )

    @staticmethod
    async def _set_new_user_tags_on_gif_internal(
            user_id: int,
            gif_id: int,
            tags: set[str],
            tag_repository: TagRepository,
            user_gif_tag_repository: UserGifTagRepository
    ) -> None:
        tags = await tag_repository.fake_upsert_tags(tags)
        tag_ids = {tag.id for tag in tags}
        
        await user_gif_tag_repository.delete_except_tag_ids(
            user_id=user_id,
            gif_id=gif_id,
            keep_tag_ids=tag_ids
        )
        
        await user_gif_tag_repository.create_many(
            [
                {
                    UserGifTag.user_id: user_id,
                    UserGifTag.gif_id: gif_id,
                    UserGifTag.tag_id: tag_id
                }
                for tag_id in tag_ids
            ],
            ignore_conflicts=True
        )

    @staticmethod
    def _get_service_cache_prefix(
            user_id: int
    ) -> str:
        return f"{UserService.get_user_cache_prefix(user_id)}:library"
