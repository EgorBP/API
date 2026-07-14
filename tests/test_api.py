import pytest
from httpx import AsyncClient


class TestUserEndpoints:
    """Тесты для endpoints работы с пользователями и их GIF."""

    @pytest.fixture
    async def sample_user_id(self):
        """Фикстура с тестовым Telegram ID пользователя."""
        return 123456789

    @pytest.fixture
    async def sample_gif_id(self):
        """Фикстура с тестовым Telegram GIF ID."""
        return "test_gif_id_12345"

    async def test_create_and_get_gif(self, client: AsyncClient, sample_user_id, sample_gif_id):
        """Тест создания GIF с тегами и последующего получения."""
        # Создаём GIF с тегами
        response = await client.put(
            f"/user/{sample_user_id}/gif/{sample_gif_id}",
            json={"tags": ["funny", "cat", "meme"]}
        )
        assert response.status_code == 204

        # Получаем созданный GIF
        response = await client.get(f"/user/{sample_user_id}/gif/{sample_gif_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["tg_gif_id"] == sample_gif_id
        assert set(data["tags"]) == {"funny", "cat", "meme"}
        assert "id" in data

    async def test_update_gif_tags(self, client: AsyncClient, sample_user_id, sample_gif_id):
        """Тест обновления тегов существующего GIF."""
        # Создаём GIF с начальными тегами
        await client.put(
            f"/user/{sample_user_id}/gif/{sample_gif_id}",
            json={"tags": ["old", "tag"]}
        )

        # Обновляем теги
        response = await client.put(
            f"/user/{sample_user_id}/gif/{sample_gif_id}",
            json={"tags": ["new", "updated", "tags"]}
        )
        assert response.status_code == 204

        # Проверяем, что теги обновились
        response = await client.get(f"/user/{sample_user_id}/gif/{sample_gif_id}")
        assert response.status_code == 200
        data = response.json()
        assert set(data["tags"]) == {"new", "updated", "tags"}

    async def test_get_nonexistent_gif(self, client: AsyncClient, sample_user_id):
        """Тест получения несуществующего GIF."""
        response = await client.get(f"/user/{sample_user_id}/gif/nonexistent_gif_id")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    async def test_delete_gif_tags(self, client: AsyncClient, sample_user_id, sample_gif_id):
        """Тест удаления всех тегов GIF."""
        # Создаём GIF с тегами
        await client.put(
            f"/user/{sample_user_id}/gif/{sample_gif_id}",
            json={"tags": ["delete", "me"]}
        )

        # Удаляем теги
        response = await client.delete(f"/user/{sample_user_id}/gif/{sample_gif_id}")
        assert response.status_code == 204

        # Проверяем, что GIF больше не найден
        response = await client.get(f"/user/{sample_user_id}/gif/{sample_gif_id}")
        assert response.status_code == 404

    async def test_get_user_tags(self, client: AsyncClient, sample_user_id):
        """Тест получения всех тегов пользователя."""
        # Создаём несколько GIF с разными тегами
        await client.put(
            f"/user/{sample_user_id}/gif/gif1",
            json={"tags": ["tag1", "tag2"]}
        )
        await client.put(
            f"/user/{sample_user_id}/gif/gif2",
            json={"tags": ["tag2", "tag3"]}
        )

        # Получаем все теги пользователя
        response = await client.get(f"/user/{sample_user_id}/tags")
        assert response.status_code == 200
        tags = response.json()
        assert isinstance(tags, list)
        assert set(tags) == {"tag1", "tag2", "tag3"}

    async def test_get_tags_for_nonexistent_user(self, client: AsyncClient):
        """Тест получения тегов для несуществующего пользователя."""
        response = await client.get("/user/999999999/tags")
        assert response.status_code == 404


class TestSearchEndpoint:
    """Тесты для endpoint поиска GIF по тегам."""

    @pytest.fixture
    async def user_with_gifs(self, client: AsyncClient):
        """Фикстура создаёт пользователя с несколькими GIF."""
        user_id = 987654321
        
        # Создаём несколько GIF с разными тегами
        await client.put(
            f"/user/{user_id}/gif/gif_cat_funny",
            json={"tags": ["cat", "funny"]}
        )
        await client.put(
            f"/user/{user_id}/gif/gif_cat_cute",
            json={"tags": ["cat", "cute"]}
        )
        await client.put(
            f"/user/{user_id}/gif/gif_dog_funny",
            json={"tags": ["dog", "funny"]}
        )
        
        return user_id

    async def test_search_without_tags(self, client: AsyncClient, user_with_gifs):
        """Тест поиска без фильтрации по тегам (все GIF пользователя)."""
        response = await client.get(f"/search?tg_user_id={user_with_gifs}")
        assert response.status_code == 200
        data = response.json()
        assert data["tg_user_id"] == user_with_gifs
        assert len(data["gifs_data"]) == 3

    async def test_search_with_single_tag(self, client: AsyncClient, user_with_gifs):
        """Тест поиска по одному тегу."""
        response = await client.get(f"/search?tg_user_id={user_with_gifs}&tags=cat")
        assert response.status_code == 200
        data = response.json()
        assert len(data["gifs_data"]) == 2
        
        # Проверяем, что все найденные GIF содержат тег "cat"
        for gif in data["gifs_data"]:
            assert "cat" in gif["tags"]

    async def test_search_with_multiple_tags(self, client: AsyncClient, user_with_gifs):
        """Тест поиска по нескольким тегам (AND логика)."""
        response = await client.get(
            f"/search?tg_user_id={user_with_gifs}&tags=cat&tags=funny"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["gifs_data"]) == 1
        
        # Проверяем, что найденный GIF содержит оба тега
        gif = data["gifs_data"][0]
        assert "cat" in gif["tags"]
        assert "funny" in gif["tags"]

    async def test_search_with_no_matches(self, client: AsyncClient, user_with_gifs):
        """Тест поиска с тегом, который не существует."""
        response = await client.get(
            f"/search?tg_user_id={user_with_gifs}&tags=nonexistent"
        )
        assert response.status_code == 404

    async def test_search_for_nonexistent_user(self, client: AsyncClient):
        """Тест поиска для несуществующего пользователя."""
        response = await client.get("/search?tg_user_id=999999999")
        assert response.status_code == 404


class TestEdgeCases:
    """Тесты граничных случаев и валидации."""

    async def test_empty_tags_list(self, client: AsyncClient):
        """Тест создания GIF с пустым списком тегов."""
        response = await client.put(
            "/user/111111/gif/test_gif",
            json={"tags": []}
        )
        assert response.status_code == 204

    async def test_duplicate_tags(self, client: AsyncClient):
        """Тест создания GIF с дублирующимися тегами."""
        user_id = 222222
        gif_id = "test_duplicate"
        
        response = await client.put(
            f"/user/{user_id}/gif/{gif_id}",
            json={"tags": ["tag1", "tag1", "tag2"]}
        )
        assert response.status_code == 204

        response = await client.get(f"/user/{user_id}/gif/{gif_id}")
        assert response.status_code == 200

    async def test_multiple_users_isolation(self, client: AsyncClient):
        """Тест изоляции данных между пользователями."""
        user1_id = 333333
        user2_id = 444444
        gif_id = "shared_gif_id"

        # Создаём одинаковый gif_id для двух пользователей
        await client.put(
            f"/user/{user1_id}/gif/{gif_id}",
            json={"tags": ["user1"]}
        )
        await client.put(
            f"/user/{user2_id}/gif/{gif_id}",
            json={"tags": ["user2"]}
        )

        # Проверяем, что у каждого пользователя свои теги
        response1 = await client.get(f"/user/{user1_id}/gif/{gif_id}")
        response2 = await client.get(f"/user/{user2_id}/gif/{gif_id}")

        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response1.json()["tags"] == ["user1"]
        assert response2.json()["tags"] == ["user2"]
