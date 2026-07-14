import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.repository import UserRepository, GifRepository, TagRepository, UserGifTagRepository
from app.models import User, Gif, Tag, UserGifTag


class TestUsersCRUD:
    """Unit тесты для UsersCRUD."""

    async def test_create_user(self, db_session: AsyncSession):
        """Тест создания пользователя."""
        crud = UserRepository(db_session)
        tg_id = 123456789
        
        user = await crud.create_user(tg_id=tg_id)
        await db_session.commit()
        
        assert user is not None
        assert user.id is not None
        assert user.tg_id == tg_id

    async def test_create_duplicate_user(self, db_session: AsyncSession):
        """Тест создания пользователя с существующим tg_id."""
        crud = UserRepository(db_session)
        tg_id = 987654321
        
        # Создаём первого пользователя
        user1 = await crud.create_user(tg_id=tg_id)
        await db_session.commit()
        
        # Пытаемся создать дубликат
        user2 = await crud.create_user(tg_id=tg_id)
        await db_session.commit()
        
        # Должен вернуться существующий пользователь
        assert user1.id == user2.id
        assert user1.tg_id == user2.tg_id

    async def test_get_user_by_tg_id(self, db_session: AsyncSession):
        """Тест получения пользователя по tg_id."""
        crud = UserRepository(db_session)
        tg_id = 111222333
        
        # Создаём пользователя
        await crud.create_user(tg_id=tg_id)
        await db_session.commit()
        
        # Получаем пользователя
        users = await crud.get_many(filters={User.tg_id: tg_id})
        
        assert len(users) == 1
        assert users[0].tg_id == tg_id

    async def test_delete_user(self, db_session: AsyncSession):
        """Тест удаления пользователя."""
        crud = UserRepository(db_session)
        tg_id = 444555666
        
        # Создаём пользователя
        user = await crud.create_user(tg_id=tg_id)
        await db_session.commit()
        
        # Удаляем пользователя
        deleted_count = await crud.delete_many(instance_id=user.id)
        await db_session.commit()
        
        assert deleted_count == 1
        
        # Проверяем, что пользователь удалён
        users = await crud.get_many(filters={User.tg_id: tg_id})
        assert len(users) == 0


class TestGifsCRUD:
    """Unit тесты для GifsCRUD."""

    async def test_create_gif(self, db_session: AsyncSession):
        """Тест создания GIF."""
        crud = GifRepository(db_session)
        tg_gif_id = "test_gif_12345"
        
        gif = await crud.create_gif(tg_gif_id=tg_gif_id)
        await db_session.commit()
        
        assert gif is not None
        assert gif.id is not None
        assert gif.tg_gif_id == tg_gif_id

    async def test_create_duplicate_gif(self, db_session: AsyncSession):
        """Тест создания GIF с существующим tg_gif_id."""
        crud = GifRepository(db_session)
        tg_gif_id = "duplicate_gif_id"
        
        # Создаём первый GIF
        gif1 = await crud.create_gif(tg_gif_id=tg_gif_id)
        await db_session.commit()
        
        # Пытаемся создать дубликат
        gif2 = await crud.create_gif(tg_gif_id=tg_gif_id)
        await db_session.commit()
        
        # Должен вернуться существующий GIF
        assert gif1.id == gif2.id
        assert gif1.tg_gif_id == gif2.tg_gif_id

    async def test_get_gif_by_tg_gif_id(self, db_session: AsyncSession):
        """Тест получения GIF по tg_gif_id."""
        crud = GifRepository(db_session)
        tg_gif_id = "search_gif_id"
        
        # Создаём GIF
        await crud.create_gif(tg_gif_id=tg_gif_id)
        await db_session.commit()
        
        # Получаем GIF
        gifs = await crud.get_many(filters={Gif.tg_gif_id: tg_gif_id})
        
        assert len(gifs) == 1
        assert gifs[0].tg_gif_id == tg_gif_id

    async def test_delete_gif(self, db_session: AsyncSession):
        """Тест удаления GIF."""
        crud = GifRepository(db_session)
        tg_gif_id = "delete_gif_id"
        
        # Создаём GIF
        gif = await crud.create_gif(tg_gif_id=tg_gif_id)
        await db_session.commit()
        
        # Удаляем GIF
        deleted_count = await crud.delete_many(instance_id=gif.id)
        await db_session.commit()
        
        assert deleted_count == 1
        
        # Проверяем, что GIF удалён
        gifs = await crud.get_many(filters={Gif.tg_gif_id: tg_gif_id})
        assert len(gifs) == 0


class TestTagsCRUD:
    """Unit тесты для TagsCRUD."""

    async def test_create_tag(self, db_session: AsyncSession):
        """Тест создания тега."""
        crud = TagRepository(db_session)
        tag_name = "funny"
        
        tag = await crud.create_tag(tag=tag_name)
        await db_session.commit()
        
        assert tag is not None
        assert tag.id is not None
        assert tag.tag == tag_name

    async def test_create_duplicate_tag(self, db_session: AsyncSession):
        """Тест создания тега с существующим именем."""
        crud = TagRepository(db_session)
        tag_name = "duplicate_tag"
        
        # Создаём первый тег
        tag1 = await crud.create_tag(tag=tag_name)
        await db_session.commit()
        
        # Пытаемся создать дубликат
        tag2 = await crud.create_tag(tag=tag_name)
        await db_session.commit()
        
        # Должен вернуться существующий тег
        assert tag1.id == tag2.id
        assert tag1.tag == tag2.tag

    async def test_get_multiple_tags(self, db_session: AsyncSession):
        """Тест получения нескольких тегов."""
        crud = TagRepository(db_session)
        tag_names = ["cat", "dog", "bird"]
        
        # Создаём несколько тегов
        for tag_name in tag_names:
            await crud.create_tag(tag=tag_name)
        await db_session.commit()
        
        # Получаем все теги
        tags = await crud.get_many(filters={Tag.tag: tag_names})
        
        assert len(tags) == 3
        retrieved_names = [tag.tag for tag in tags]
        assert set(retrieved_names) == set(tag_names)


class TestUserGifTagCRUD:
    """Unit тесты для UserGifTagCRUD."""

    @pytest.fixture
    async def setup_entities(self, db_session: AsyncSession):
        """Фикстура создаёт пользователя, GIF и тег для тестов."""
        user_crud = UserRepository(db_session)
        gif_crud = GifRepository(db_session)
        tag_crud = TagRepository(db_session)
        
        user = await user_crud.create_user(tg_id=123456)
        gif = await gif_crud.create_gif(tg_gif_id="test_gif")
        tag = await tag_crud.create_tag(tag="test_tag")
        await db_session.commit()
        
        return {
            "user_id": user.id,
            "gif_id": gif.id,
            "tag_id": tag.id,
        }

    async def test_create_user_gif_tag(self, db_session: AsyncSession, setup_entities):
        """Тест создания связи пользователь-GIF-тег."""
        crud = UserGifTagRepository(db_session)
        
        relation = await crud.create_user_gif_tag(
            user_id=setup_entities["user_id"],
            gif_id=setup_entities["gif_id"],
            tag_id=setup_entities["tag_id"],
        )
        await db_session.commit()
        
        assert relation is not None
        assert relation.user_id == setup_entities["user_id"]
        assert relation.gif_id == setup_entities["gif_id"]
        assert relation.tag_id == setup_entities["tag_id"]

    async def test_create_duplicate_user_gif_tag(self, db_session: AsyncSession, setup_entities):
        """Тест создания дублирующейся связи."""
        crud = UserGifTagRepository(db_session)
        
        # Создаём первую связь
        relation1 = await crud.create_user_gif_tag(
            user_id=setup_entities["user_id"],
            gif_id=setup_entities["gif_id"],
            tag_id=setup_entities["tag_id"],
        )
        await db_session.commit()
        
        # Пытаемся создать дубликат
        relation2 = await crud.create_user_gif_tag(
            user_id=setup_entities["user_id"],
            gif_id=setup_entities["gif_id"],
            tag_id=setup_entities["tag_id"],
        )
        await db_session.commit()
        
        # Должна вернуться существующая связь
        assert relation1.user_id == relation2.user_id
        assert relation1.gif_id == relation2.gif_id
        assert relation1.tag_id == relation2.tag_id

    async def test_delete_user_gif_tag(self, db_session: AsyncSession, setup_entities):
        """Тест удаления связи пользователь-GIF-тег."""
        crud = UserGifTagRepository(db_session)
        
        # Создаём связь
        await crud.create_user_gif_tag(
            user_id=setup_entities["user_id"],
            gif_id=setup_entities["gif_id"],
            tag_id=setup_entities["tag_id"],
        )
        await db_session.commit()
        
        # Удаляем связь
        deleted_count = await crud.delete_many(
            filters={
                UserGifTag.user_id: setup_entities["user_id"],
                UserGifTag.gif_id: setup_entities["gif_id"],
                UserGifTag.tag_id: setup_entities["tag_id"],
            }
        )
        await db_session.commit()
        
        assert deleted_count == 1
        
        # Проверяем, что связь удалена
        relations = await crud.get_many(
            filters={
                UserGifTag.user_id: setup_entities["user_id"],
                UserGifTag.gif_id: setup_entities["gif_id"],
            }
        )
        assert len(relations) == 0

    async def test_cascade_delete(self, db_session: AsyncSession, setup_entities):
        """Тест каскадного удаления при удалении пользователя."""
        user_crud = UserRepository(db_session)
        ugt_crud = UserGifTagRepository(db_session)
        
        # Создаём связь
        await ugt_crud.create_user_gif_tag(
            user_id=setup_entities["user_id"],
            gif_id=setup_entities["gif_id"],
            tag_id=setup_entities["tag_id"],
        )
        await db_session.commit()
        
        # Удаляем пользователя
        await user_crud.delete_many(instance_id=setup_entities["user_id"])
        await db_session.commit()
        
        # Проверяем, что связь тоже удалена (CASCADE)
        relations = await ugt_crud.get_many(
            filters={UserGifTag.user_id: setup_entities["user_id"]}
        )
        assert len(relations) == 0
