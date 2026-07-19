import hashlib
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Sequence
from redis.asyncio import Redis
import json
import logging

from app.core.exceptions import UserGifsNotFoundError, GifNotFoundError, UserTagsNotFoundError
from app.models import UserGifTag, User, Gif, Tag
from app.schemas.common import UserGifsCursorPaginatedResponse, CursorPaginatedResponse, CursorPaginationMeta
from app.schemas.users import UserOut
from app.schemas.gifs import GifOut, GifCreate, GifUpdate
from app.repositories import UserRepository, UserGifTagRepository, TagRepository, GifRepository, SearchRepository
from app.services.interfaces import StorageProvider

logger = logging.getLogger("app.service.users")


# TODO: update dockstring
class UserService:
    def __init__(
            self,
            session: AsyncSession,
            redis: Redis,
            storage: StorageProvider,
            user_id: int,
    ):
        self.storage = storage
        self.user_id = user_id
        
        self.session = session
        self.redis = redis
        self.base_user_cache_path = f"user_id:{self.user_id}"
        
    async def get_user_gifs_with_tags(
            self,
            limit: int,
            gif_ids: Sequence[int] | int | None  = None,
            tags: set[str] | str | None = None,
            cursor_id: int | None = None
    ) -> UserGifsCursorPaginatedResponse | None:
        """
        Возвращает гифки пользователя с их тегами в виде вложенного словаря.
    
        Формируемая структура:  
        
        {
            'id': внутренний ID пользователя,
    
            'tg_user_id': Telegram ID пользователя,
    
            'gifs': [
                {
                    'id': внутренний ID гифки,
    
                    'tg_gif_id': Telegram ID гифки,
    
                    'tags': [список тегов]
                },
    
                ...
            ]
            
        }
    
        Таблицы `users`, `gifs`, `tags` и `user_gif_tags` связываются через JOIN.
        Фильтрация возможна по:
          - `user_id` (внутренний ID в базе),
          - `tg_user_id` (Telegram ID пользователя),
          - `gif_ids` (ID гифок в базе, возвращаются только указанные гифки),
          - `tags` (возвращаются только гифки, содержащие все теги).
    
        Если указаны одновременно `user_id` и `tg_user_id`, приоритет имеет `user_id`.
    
        :param async_session: Объект асинхронной сессии SQLAlchemy.
        :param redis: Объект асинхронной сессии Redis.
        :param user_id: Внутренний ID пользователя (опционально).
        :param tg_user_id: Telegram ID пользователя (опционально).
        :param gif_ids: Один или несколько ID гифок для фильтрации (опционально).
        :param tags: Один или несколько тегов для фильтрации гифок (опционально).
        :return: Словарь с данными пользователя, гифок и тегов в формате, описанном выше,
                 или None, если пользователь не найден.
        """
        search_repository = SearchRepository(self.session)
        
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

        cursor_string = str(cursor_id) if cursor_id is not None else "first_page"
        cache_key = f"{self.base_user_cache_path}:gif_ids:{gif_ids_string}:tags:{tags_string}:cursor:{cursor_string}:limit:{limit}"
    
        cached_data = await self.redis.get(cache_key)
        if cached_data:
            logger.info(
                "Get user gifs with tags from cache",
                extra={
                    "source": "database",
                    "user_id": self.user_id,
                }
            )
            return UserGifsCursorPaginatedResponse.model_validate_json(cached_data)
        
        rows = await search_repository.search_user_gifs_with_tags(
            user_id=self.user_id,
            gif_ids=gif_ids,
            tags=tags,
            cursor_id=cursor_id,
            limit=limit + 1
        )
        
        if not rows:
            raise UserGifsNotFoundError(
                source="database",
                user_id=self.user_id,
            )
        
        if len(rows) > limit:
            rows = rows[:limit]
            next_cursor = rows[-1].id
            has_next = True
        else:
            next_cursor = None
            has_next = False
        
        gifs_data = [
            GifOut.model_validate(row._mapping)
            for row in rows
        ]
        
        final_data = UserGifsCursorPaginatedResponse(
            user=UserOut(
                id=self.user_id
            ),
            gifs=CursorPaginatedResponse[GifOut, int](
                data=gifs_data,
                pagination=CursorPaginationMeta[int](
                    limit=limit,
                    has_next=has_next,
                    next_cursor=next_cursor,
                )
            )
        )
        
        await self.redis.set(cache_key, final_data.model_dump_json(), ex=300)
        
        logger.info(
            "Set new cache for 300s",
            extra={
                "user_id": self.user_id,
            }
        )
        logger.info(
            "Get user gifs with tags from database",
            extra={
                "source": "database",
                "user_id": self.user_id,
            }
        )
    
        return final_data
    
    async def get_all_user_tags(
            self,
    ) -> set[str]:
        """
        Возвращает все уникальные теги, связанные с GIF пользователя.
    
        :return: Множество уникальных тегов (`set[str]`) или None, если пользователь не найден.
        """
        user_gif_tag_repository = UserGifTagRepository(self.session)

        cache_key = f"user_id:{self.user_id}:all_user_tags"
        
        cached_data = await self.redis.get(cache_key)
        if cached_data:
            logger.info(
                "Get all user tags from cache",
                extra={
                    "source": "cache",
                    "user_id": self.user_id,
                }
            )
            return json.loads(cached_data)
        
        tags = await user_gif_tag_repository.get_many_with_join(
            columns=[
                Tag.tag
            ],
            join_models=[
                Tag
            ],
            filters={UserGifTag.user_id: self.user_id},
            scalars=True
        )
    
        if not tags:
            logger.info(
                "Tags not found",
                extra={
                    "source": "database",
                    "user_id": self.user_id,
                }
            )
            raise UserTagsNotFoundError(self.user_id)
        
        tags = list(tags)
    
        await self.redis.set(cache_key, json.dumps(tags), ex=300)
    
        logger.info(
            "Set new cache for 300s",
            extra={
                "user_id": self.user_id,
            }
        )
        logger.info(
            "Get all user tags from database",
            extra={
                "source": "database",
                "user_id": self.user_id,
            }
        )
    
        return set(tags)
    
    async def add_new_user_gif(
            self,
            gif_file: UploadFile,
            gif_create: GifCreate
    ) -> GifOut:
        tag_repository = TagRepository(self.session)
        gif_repository = GifRepository(self.session)
        user_gif_tag_repository = UserGifTagRepository(self.session)
        
        tags = gif_create.tags
        
        filename, file_hash = await self._create_unique_filename_and_hash(gif_file)
        
        gif = await gif_repository.get_one_orm(
            filters={Gif.file_hash: file_hash}
        )
        
        try:
            if gif is None:
                file_path = await self.storage.save_file(gif_file, filename)
                gif = await gif_repository.create_gif(
                    file_path=file_path,
                    file_hash=file_hash
                )
                logger.info(
                    "Create new gif",
                    extra={
                        "user_id": self.user_id,
                        "gif_id": gif.id
                    },
                    
                )
            
            gif_id = gif.id
            await self._set_new_user_tags_on_gif_internal(
                gif_id=gif_id,
                gif_update=GifUpdate(tags=tags),
                tag_repository=tag_repository,
                user_gif_tag_repository=user_gif_tag_repository
            )

            await self.session.commit()
    
            return GifOut(
                id=gif_id,
                file_path=gif.file_path,
                tags=tags
            )
        
        except Exception:
            await self.session.rollback()
            logger.exception(
                "Error when create new GIF",
                extra={
                    "user_id": self.user_id,
                }
            )
            raise

    async def set_new_user_tags_on_gif(
            self,
            gif_id: int,
            gif_update: GifUpdate,
    ) -> None:
        """
        Добавляет (или обновляет) связь между пользователем, гифкой и её тегами.
        Делает commit если операция прошла успешно и rollback в случае возникновения ошибок. 
    
        Функция гарантирует, что:
    
        - если какого-либо поля не было в нужной таблице, оно автоматически создастся.
        - для каждой комбинации (user, gif, tag) создастся запись в таблице `user_gif_tags`.
        - старые теги будут удалены.
    
        :param gif_id: Telegram ID гифки.
        :param tags: Один тег или список тегов, которые будут связаны с гифкой.
        :return: None (изменения фиксируются в базе данных через session).
        """
        tag_repository = TagRepository(self.session)
        user_gif_tag_repository = UserGifTagRepository(self.session)
        gif_repository = GifRepository(self.session)
        
        if await gif_repository.get_one(
                columns=Gif.id,
                filters={Gif.id: gif_id}
        ):
            await self._set_new_user_tags_on_gif_internal(
                gif_id=gif_id,
                gif_update=gif_update,
                tag_repository=tag_repository,
                user_gif_tag_repository=user_gif_tag_repository
            )
        else:
            raise GifNotFoundError(
                gif_id=gif_id,
                user_id=self.user_id
            )
    
    async def unlink_user_from_gif(
            self,
            gif_ids: list[int],
    ) -> int:
        """
        Удаляет GIF вместе с тегами для конкретного пользователя. 
        Делает commit если операция прошла успешно и rollback в случае возникновения ошибок.
        
        Удаляет весь кэш пользователя.
    
        :param gif_ids: ID для GIF которое нужно удалить у юзера.
    
        :return: Количество удаленных строк
        """
        user_gif_tag_repository = UserGifTagRepository(self.session)
        
        try:
            result = await user_gif_tag_repository.delete_many(
                filters={
                    UserGifTag.user_id: self.user_id,
                    UserGifTag.gif_id: gif_ids,
                }
            )
            await self.session.commit()
            logger.info(
                f"{result} user GIFs deleted",
                extra={
                    "user_id": self.user_id,
                }
            )
            
            await self._invalidate_all_user_cache()  
                
            return result
        
        except Exception:
            await self.session.rollback()
            logger.exception(
                "Error when delete user GIF and tags",
                extra={
                    "user_id": self.user_id,
                }
            )
            raise

    async def _invalidate_all_user_cache(
            self
    ):
        keys = []
        objects_count = 0
        batch_size = 500

        async for key in self.redis.scan_iter(f"{self.base_user_cache_path}:*"):
            keys.append(key)

            if len(keys) >= batch_size:
                await self.redis.unlink(*keys)
                objects_count += len(keys)
                keys = []

        if keys:
            objects_count += len(keys)
            await self.redis.unlink(*keys)

        logger.info(
            f"User cache ({objects_count} elements) invalidated",
            extra={
                "user_id": self.user_id,
            }
        )

    async def _create_unique_filename_and_hash(
            self,
            file: UploadFile
    ) -> tuple[str, str]:
        await file.seek(0)

        sha256_hash = hashlib.sha256()
        while chunk := await file.read(1024 * 1024):
            sha256_hash.update(chunk)

        file_hash = sha256_hash.hexdigest()

        await file.seek(0)

        file_ext = file.filename.split(".")[-1] if "." in file.filename else "gif"
        unique_filename = f"{file_hash}.{file_ext.lower()}"

        return unique_filename, file_hash

    async def _set_new_user_tags_on_gif_internal(
            self,
            gif_id: int,
            gif_update: GifUpdate,
            tag_repository: TagRepository,
            user_gif_tag_repository: UserGifTagRepository
    ) -> None:
        tags = gif_update.tags

        try:
            # Вставляем теги
            await tag_repository.create_many(
                [
                    {Tag.tag: tag}
                    for tag in tags
                ],
                ignore_conflicts=True
            )

            # Получаем tag_id
            tag_ids = await tag_repository.get_many(
                columns=Tag.id,
                filters={
                    Tag.tag: tags
                },
                scalars=True
            )

            # Снимаем связь между старыми тегами и гифкой
            await user_gif_tag_repository.delete_many(
                filters={
                    UserGifTag.user_id: self.user_id,
                    UserGifTag.gif_id: gif_id,
                }
            )

            # Создаем связь между новыми тегами, GIF и пользователем
            await user_gif_tag_repository.create_many(
                [
                    {
                        UserGifTag.user_id: self.user_id,
                        UserGifTag.gif_id: gif_id,
                        UserGifTag.tag_id: tag_id
                    }
                    for tag_id in tag_ids
                ]
            )

            await self.session.commit()
            logger.info(
                "User GIF tags updated",
                extra={
                    "user_id": self.user_id,
                    "gif_id": gif_id
                }
            )

            # Инвалидируем кэш
            await self._invalidate_all_user_cache()

        except Exception:
            await self.session.rollback()
            logger.exception(
                "Error when update tags for user GIF",
                extra={
                    "user_id": self.user_id,
                    "gif_id": gif_id
                }
            )
            raise
