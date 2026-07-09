import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import UserGifTag, User, Gif, Tag
from app.crud import UsersCRUD, UserGifTagCRUD, TagsCRUD, GifsCRUD
from typing import Sequence
from redis.asyncio import Redis
import json


async def get_user_gifs_with_tags(
        async_session: AsyncSession,
        redis: Redis,
        user_id: int | None = None,
        tg_user_id: int | None = None,
        tg_gifs_id: Sequence[str] | str = None,
        tags: Sequence[str] | str = None,
):
    """
    Возвращает гифки пользователя с их тегами в виде вложенного словаря.

    Формируемая структура:  
    
    {
        'id': внутренний ID пользователя,

        'tg_user_id': Telegram ID пользователя,

        'gifs_data': [
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
      - `tg_gifs_id` (Telegram ID гифок, возвращаются только указанные гифки),
      - `tags` (возвращаются только гифки, содержащие все теги).

    Если указаны одновременно `user_id` и `tg_user_id`, приоритет имеет `user_id`.

    :param async_session: Объект асинхронной сессии SQLAlchemy.
    :param redis: Объект асинхронной сессии Redis.
    :param user_id: внутренний ID пользователя (опционально).
    :param tg_user_id: Telegram ID пользователя (опционально).
    :param tg_gifs_id: один или несколько Telegram ID гифок для фильтрации (опционально).
    :param tags: один или несколько тегов для фильтрации гифок (опционально).
    :return: словарь с данными пользователя, гифок и тегов в формате, описанном выше,
             или None, если пользователь не найден.
    """
    if user_id is None and tg_user_id is None:
        raise KeyError("Необходимо передать user_id или tg_user_id")
    
    user_gif_tag_crud = UserGifTagCRUD(async_session)

    if isinstance(tg_gifs_id, str):
        tg_gifs_id = (tg_gifs_id,)

    if isinstance(tags, str):
        tags = (tags,)

    # Кеширование
    tags = tags or []
    normalized_tags = sorted([tag.strip() for tag in tags])
    tags_string = ",".join(normalized_tags) if normalized_tags else "all"
    tg_gifs_id = tg_gifs_id or []
    normalized_tg_gifs_id = sorted([tg_gif_id.strip() for tg_gif_id in tg_gifs_id])
    tg_gifs_id_string = ",".join(normalized_tg_gifs_id) if normalized_tg_gifs_id else "all"

    cache_key_template = "tg_user_id:{{tg_user_id}}:tg_gifs_id:{tg_gifs_id_string}:tags:{tags_string}"
    cache_key_template = cache_key_template.format(tags_string=tags_string, tg_gifs_id_string=tg_gifs_id_string)

    if not tg_user_id:
        tg_user_id = await redis.get(f"user_id:{user_id}")
    if tg_user_id:
        cache_key = cache_key_template.format(tg_user_id=tg_user_id)
        cached_data = await redis.get(cache_key)
        if cached_data:
            return json.loads(cached_data)
    
    filters = {}
    if tg_gifs_id:
        filters[Gif.tg_gif_id] = tg_gifs_id
    if user_id is not None:
        filters[UserGifTag.user_id] = user_id
    else:
        filters[User.tg_id] = tg_user_id

    rows = await user_gif_tag_crud.get_instances_with_join(
        select_columns=[
            UserGifTag.user_id,
            UserGifTag.gif_id,
            User.tg_id,
            Gif.tg_gif_id,
            Tag.tag
        ],
        join_models=[
            User, 
            Gif, 
            Tag
        ],
        filters=filters
    )
    
    if not rows:
        return None

    first = rows[0]
    resolved_user_id = user_id if user_id is not None else first.user_id
    resolved_tg_user_id = tg_user_id if tg_user_id is not None else first.tg_id
    
    cache_key = cache_key_template.format(tg_user_id=resolved_tg_user_id)
    await redis.set(f"user_id:{user_id}", resolved_tg_user_id, ex=600)

    gifs_map: dict[int, dict] = {}

    for row in rows:
        gif = gifs_map.setdefault(
            row.gif_id,
            {
                'id': row.gif_id,
                'tg_gif_id': row.tg_gif_id,
                'tags': [],
            }
        )
        gif['tags'].append(row.tag)

    gifs_data = list(gifs_map.values())

    if tags:
        tags_set = set(tags)
        gifs_data = [
            gif for gif in gifs_data
            if tags_set.issubset(set(gif['tags']))
        ]
        
    final_data = {
        'id': resolved_user_id,
        'tg_user_id': resolved_tg_user_id,
        'gifs_data': gifs_data,
    }
    
    await redis.set(cache_key, json.dumps(final_data), ex=300)

    return final_data


async def get_all_user_tags(
        async_session: AsyncSession,
        redis: Redis,
        # user_id: int | None = None,
        tg_user_id: int,
):
    """
    Возвращает все уникальные теги, связанные с GIF пользователя.

    :param async_session: Объект асинхронной сессии SQLAlchemy.
    :param redis: Объект асинхронной сессии Redis.
    :param tg_user_id: Telegram ID пользователя.
    :return: Множество уникальных тегов (`set[str]`) или None, если пользователь не найден.
    """
    # if user_id is None and tg_user_id is None:
    #     raise KeyError("Необходимо передать user_id или tg_user_id")
    
    user_gif_tag_crud = UserGifTagCRUD(async_session)

    cache_key_template = "tg_user_id:{tg_user_id}:all_user_tags"
    
    # if not tg_user_id:
    #     tg_user_id = await redis.get(f"user_id:{user_id}")
    # if tg_user_id:
    cache_key = cache_key_template.format(tg_user_id=tg_user_id)
    cached_data = await redis.get(cache_key)
    if cached_data:
        return json.loads(cached_data)
    
    filters = {}
    join_models = [Tag]
    # if user_id is not None:
    #     filters[UserGifTag.user_id] = user_id
    # else:
    join_models.append(User)
    filters[User.tg_id] = tg_user_id

    tags = await user_gif_tag_crud.get_instances_with_join(
        select_columns=[
            Tag.tag
        ],
        join_models=join_models,
        filters=filters,
        scalar=True
    )

    if not tags:
        return None
    tags = list(set(tags))

    # resolved_tg_user_id = tg_user_id if tg_user_id is not None else result.scalars().tg_id
    # cache_key = cache_key_template.format(tg_user_id=resolved_tg_user_id)
    # await redis.set(f"user_id:{user_id}", resolved_tg_user_id, ex=600)
    await redis.set(cache_key, json.dumps(tags), ex=300)

    return tags


async def set_new_user_tags_on_gif(
        async_session: AsyncSession,
        redis: Redis,
        tg_user_id: int,
        tg_gif_id: str,
        tags: Sequence[str] | str,
):
    """
    Добавляет (или обновляет) связь между пользователем, гифкой и её тегами.
    Делает commit если операция прошла успешно и rollback в случае возникновения ошибок. 

    Функция гарантирует, что:

    - если какого-либо поля не было в нужной таблице, оно автоматически создастся.
    - для каждой комбинации (user, gif, tag) создастся запись в таблице `user_gif_tags`.
    - старые теги будут удалены.

    :param async_session: Объект асинхронной сессии SQLAlchemy.
    :param redis: Объект асинхронной сессии Redis.
    :param tg_user_id: Telegram ID пользователя.
    :param tg_gif_id: Telegram ID гифки.
    :param tags: Один тег или список тегов, которые будут связаны с гифкой.
    :return: None (изменения фиксируются в базе данных через session).
    """
    
    user_gif_tag_crud = UserGifTagCRUD(async_session)
    users_crud = UsersCRUD(async_session)
    tags_crud = TagsCRUD(async_session)
    gifs_crud = GifsCRUD(async_session)
    if isinstance(tags, (str, tuple)):
        tags = [tags]

    old_data = await get_user_gifs_with_tags(async_session, redis, tg_user_id=tg_user_id, tg_gifs_id=tg_gif_id)

    # TODO: Можно оптимизировать, но нужно улучшать CRUD
    # Удаляем старые ненужные теги
    try:
        if old_data and old_data['gifs_data']:
            for old_tag in old_data['gifs_data'][0]['tags']:
                if not old_tag in tags:
                    tag_id = (await tags_crud.get_instances(columns=Tag.id, filters={Tag.tag: old_tag}))[0][0]
                    await user_gif_tag_crud.delete_instances(filters={
                        UserGifTag.user_id: old_data['id'],
                        UserGifTag.gif_id: old_data['gifs_data'][0]['id'],
                        UserGifTag.tag_id: tag_id,
                    })
                else:
                    tags.remove(old_tag)

        user = await users_crud.create_user(tg_user_id)
        gif = await gifs_crud.create_gif(tg_gif_id)
        tags = await asyncio.gather(
            *(tags_crud.create_tag(tag) for tag in tags)
        )
        
        await asyncio.gather(
            *(user_gif_tag_crud.create_user_gif_tag(user_id=user.id, gif_id=gif.id, tag_id=tag.id) for tag in tags)
        )

        keys = []
        async for key in redis.scan_iter(f"tg_user_id:{tg_user_id}:*"):
            keys.append(key)
        if keys:
            await redis.unlink(*keys)

        await async_session.commit()
    except Exception:
        await async_session.rollback()
        raise


async def delete_user_gif_tags(
        async_session: AsyncSession,
        redis: Redis,
        tg_user_id: int,
        gif_id: str,
        gif_id_type: str | None = None
):
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
    gifs_crud = GifsCRUD(async_session)
    users_crud = UsersCRUD(async_session)
    user_gif_tag_crud = UserGifTagCRUD(async_session)
    
    if not gif_id_type or gif_id_type == 'tg':
        try:
            gif_id = (await gifs_crud.get_instances(columns=Gif.id, filters={Gif.tg_gif_id: gif_id}))[0][0]
        except IndexError:
            return None
    elif gif_id_type == 'db':
        gif_id = int(gif_id)
    
    users_id = (await users_crud.get_instances(columns=User.id, filters={User.tg_id: tg_user_id}))[0][0]
    
    try:
        result = await user_gif_tag_crud.delete_instances(filters={
            UserGifTag.user_id: users_id,
            UserGifTag.gif_id: gif_id,
        })
        await async_session.commit()
        
        keys = []
        async for key in redis.scan_iter(f"tg_user_id:{tg_user_id}:*"):
            keys.append(key)
        if keys:
            await redis.unlink(*keys)     
            
        return result
    
    except Exception:
        await async_session.rollback()
        raise
