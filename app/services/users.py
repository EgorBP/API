from sqlalchemy.ext.asyncio import AsyncSession
from typing import Sequence
from redis.asyncio import Redis
import json
import logging

from app.core.exceptions import UserGifsNotFoundError
from app.models import UserGifTag, User, Gif, Tag
from app.schemas.common import UserGifsCursorPaginatedResponse, CursorPaginatedResponse, CursorPaginationMeta
from app.schemas.users import UserOut
from app.schemas.gifs import GifOut
from app.repositories import UserRepository, UserGifTagRepository, TagRepository, GifRepository, SearchRepository

logger = logging.getLogger("app.service.users")


# TODO: update dockstring
class UserService:
    def __init__(
            self,
            session: AsyncSession,
            redis: Redis,
            user_id: int,
    ):
        self.session = session
        self.redis = redis
        self.user_id = user_id

        self.user_gif_tag_repository = UserGifTagRepository(self.session)
        self.user_repository = UserRepository(self.session)
        self.tag_repository = TagRepository(self.session)
        self.gif_repository = GifRepository(self.session)
        self.search_repository = SearchRepository(self.session)

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
        cache_key = f"user_id:{self.user_id}:gif_ids:{gif_ids_string}:tags:{tags_string}:cursor:{cursor_string}:limit:{limit}"
    
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
        
        rows = await self.search_repository.search_user_gifs_with_tags(
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
            GifOut(
                id=row.gif_id,
                tg_gif_id=row.tg_gif_id,
                tags=row.tags
            )
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
    ) -> set[str] | None:
        """
        Возвращает все уникальные теги, связанные с GIF пользователя.
    
        :return: Множество уникальных тегов (`set[str]`) или None, если пользователь не найден.
        """
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
        
        tags = await self.user_gif_tag_repository.get_many_with_join(
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
            return None
        tags = list(set(tags))
    
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
    
        return tags
    
    async def add_new_user_gif(
            self,
            user_id: int | None = None,
            
    ):
        pass
    
    async def set_new_user_tags_on_gif(
            self,
            tg_user_id: int,
            gif_id: int,
            tags: set[str] | str,
    ) -> None:
        """
        Добавляет (или обновляет) связь между пользователем, гифкой и её тегами.
        Делает commit если операция прошла успешно и rollback в случае возникновения ошибок. 
    
        Функция гарантирует, что:
    
        - если какого-либо поля не было в нужной таблице, оно автоматически создастся.
        - для каждой комбинации (user, gif, tag) создастся запись в таблице `user_gif_tags`.
        - старые теги будут удалены.
    
        :param tg_user_id: Telegram ID пользователя.
        :param gif_id: Telegram ID гифки.
        :param tags: Один тег или список тегов, которые будут связаны с гифкой.
        :return: None (изменения фиксируются в базе данных через session).
        """
        
        tags = {tags} if isinstance(tags, str) else set(tags)
    
        old_data = await self.get_user_gifs_with_tags(tg_user_id=tg_user_id, gif_ids=gif_id, limit=1)
        
        delete_tags = set()
        new_tags = tags
        if old_data:
            old_tags = set(old_data.gifs_data[0].tags)
            if old_tags:
                delete_tags = old_tags - tags
                new_tags = tags - old_tags
        
        needed_tags = delete_tags | new_tags
    
        try:
            # Вставляем новые теги
            if new_tags:
                await self.tag_repository.create_many(
                    [
                        {Tag.tag: tag}
                        for tag in new_tags
                    ],
                    ignore_conflicts=True
                )
            
            # Получаем tag_id и расфасовываем
            rows = await self.tag_repository.get_many(
                columns=(Tag.id, Tag.tag),
                filters={
                    Tag.tag: needed_tags
                }
            )
            tag_to_id = {
                row.tag: row.id
                for row in rows
            }
            delete_tags_ids = [
                tag_to_id[tag]
                for tag in delete_tags
            ]
            new_tags_ids = [
                tag_to_id[tag]
                for tag in new_tags
            ]
            
            # Создаем пользователя и GIF
            if not old_data:
                user = await self.user_repository.create_user(tg_user_id)
                gif = await self.gif_repository.create_gif(gif_id)
            
            # Снимаем связь между старыми тегами и гифкой
            if delete_tags:
                await self.user_gif_tag_repository.delete_many(
                    filters={
                        UserGifTag.user_id: old_data.id,
                        UserGifTag.gif_id: old_data.gifs_data[0].id,
                        UserGifTag.tag_id: delete_tags_ids,
                    }
                )
            
            # Создаем связь между новыми тегами, GIF и пользователем
            if new_tags_ids:
                await self.user_gif_tag_repository.create_many(
                    [
                        {
                            UserGifTag.user_id: old_data.id if old_data else user.id,
                            UserGifTag.gif_id: old_data.gifs_data[0].id if old_data else gif.id,
                            UserGifTag.tag_id: new_tag_id
                        }
                        for new_tag_id in new_tags_ids
                    ]
                )
            
            await self.session.commit()
            logger.info(
                "User GIF tags updated",
                extra={
                    "tg_user_id": tg_user_id,
                }
            )
            
            # Инвалидируем кэш
            keys = []
            async for key in self.redis.scan_iter(f"tg_user_id:{tg_user_id}:*"):
                keys.append(key)
            if keys:
                await self.redis.unlink(*keys)
            logger.info(
                "User cache invalidated",
                extra={
                    "tg_user_id": tg_user_id,
                }
            )
        
        except Exception:
            await self.session.rollback()
            logger.exception(
                "Error when update tags for user GIF",
                extra={
                    "tg_user_id": tg_user_id,
                }
            )
            raise
    
    async def delete_user_gif_tags(
            self,
            tg_user_id: int,
            gif_id: str,
            gif_id_type: str | None = None
    ) -> int | None:
        """
        Удаляет GIF вместе с тегами для конкретного пользователя. 
        Делает commit если операция прошла успешно и rollback в случае возникновения ошибок.
        
        Удаляет весь кэш пользователя.
    
        :param async_session: Объект асинхронной сессии SQLAlchemy.
        :param redis: Объект асинхронной сессии Redis.
        :param tg_user_id: Telegram ID пользователя.
        :param gif_id: ID для GIF которое нужно удалить у юзера.
        :param gif_id_type: Тип ID: 'tg' - Telegram ID, 'db' - ID из внутренней базы.
    
        :return: Количество удаленных строк
        """
        if not gif_id_type or gif_id_type == 'tg':
            gif_id = await self.gif_repository.get_many(columns=Gif.id, filters={Gif.tg_gif_id: gif_id})
            if gif_id:
                gif_id = gif_id[0][0]
            else:
                logger.info(
                    "Gif not found",
                    extra={
                        "source": "database",
                        "tg_user_id": tg_user_id,
                        "gif_id": gif_id,
                        "gif_id_type": gif_id_type
                    }
                )
                return None
        elif gif_id_type == 'db':
            gif_id = int(gif_id)
        
        
        user_id = await self.user_repository.get_many(columns=User.id, filters={User.tg_id: tg_user_id})
        if user_id:
            logger.info(
                "User to not found",
                extra={
                    "source": "database",
                    "tg_user_id": tg_user_id,
                    "gif_id": gif_id,
                    "gif_id_type": gif_id_type
                }
            )
    
            user_id = user_id[0][0]
        else:
            return None
        
        try:
            result = await self.user_gif_tag_repository.delete_many(filters={
                UserGifTag.user_id: user_id,
                UserGifTag.gif_id: gif_id,
            })
            await self.session.commit()
            logger.info(
                "User GIF deleted",
                extra={
                    "tg_user_id": tg_user_id,
                    "gif_id": gif_id,
                    "gif_id_type": gif_id_type
                }
            )
            
            keys = []
            async for key in self.redis.scan_iter(f"tg_user_id:{tg_user_id}:*"):
                keys.append(key)
            if keys:
                await self.redis.unlink(*keys)   
            logger.info(
                "User cache invalidated",
                extra={
                    "tg_user_id": tg_user_id,
                }
            )
                
            return result
        
        except Exception:
            await self.session.rollback()
            logger.exception(
                "Error when delete user GIF and tags",
                extra={
                    "tg_user_id": tg_user_id,
                }
            )
            raise
