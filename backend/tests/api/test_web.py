"""Tests for the web-facing, JWT-authenticated user API
(`/api/v1/web/users/me/...`).
"""

from httpx import AsyncClient

from tests.helpers import GIF_BYTES


class TestGetUserInfo:

    async def test_returns_authenticated_users_info(self, web_client: AsyncClient):
        response = await web_client.get("/api/v1/web/users/me")
        assert response.status_code == 200
        assert response.json()["id"] == web_client.user_id


class TestUploadAndListGifs:

    async def test_upload_and_list_own_gif(self, web_client: AsyncClient):
        upload = await web_client.post(
            "/api/v1/web/users/me/gifs/new",
            files={"file": ("test.gif", GIF_BYTES, "image/gif")},
            data={"tags": ["cat", "funny"]},
        )
        assert upload.status_code == 200
        assert set(upload.json()["tags"]) == {"cat", "funny"}

        gifs = await web_client.get("/api/v1/web/users/me/gifs")
        assert len(gifs.json()["data"]) == 1

    async def test_gifs_count_reflects_uploads(self, web_client: AsyncClient):
        await web_client.post(
            "/api/v1/web/users/me/gifs/new",
            files={"file": ("a.gif", GIF_BYTES + b"a", "image/gif")},
            data={"tags": ["one"]},
        )
        response = await web_client.get("/api/v1/web/users/me/gifs/count")
        assert response.json() == 1

    async def test_upload_requires_valid_gif_content(self, web_client: AsyncClient):
        response = await web_client.post(
            "/api/v1/web/users/me/gifs/new",
            files={"file": ("fake.gif", b"not a gif", "image/gif")},
            data={"tags": ["cat"]},
        )
        assert response.status_code == 400

    async def test_other_users_gifs_are_not_visible(self, web_client: AsyncClient, make_access_token, db_session):
        from app.repositories.user import UserRepository

        other_user = await UserRepository(db_session).create_user(tg_id=222000222)
        await db_session.commit()

        await web_client.post(
            "/api/v1/web/users/me/gifs/new",
            files={"file": ("mine.gif", GIF_BYTES + b"mine", "image/gif")},
            data={"tags": ["private"]},
        )

        other_gifs = await web_client.get(
            "/api/v1/web/users/me/gifs",
            headers={"Authorization": f"Bearer {make_access_token(other_user.id)}"},
        )
        assert other_gifs.json()["data"] == []


class TestUserTags:

    async def test_lists_all_distinct_tags(self, web_client: AsyncClient):
        await web_client.post(
            "/api/v1/web/users/me/gifs/new",
            files={"file": ("a.gif", GIF_BYTES + b"a", "image/gif")},
            data={"tags": ["one", "two"]},
        )
        response = await web_client.get("/api/v1/web/users/me/tags/all")
        assert set(response.json()["tags"]) == {"one", "two"}


class TestUpdateAndDeleteGif:

    async def test_replace_tags_on_own_gif(self, web_client: AsyncClient):
        upload = await web_client.post(
            "/api/v1/web/users/me/gifs/new",
            files={"file": ("test.gif", GIF_BYTES, "image/gif")},
            data={"tags": ["old"]},
        )
        gif_id = upload.json()["id"]

        response = await web_client.put(
            f"/api/v1/web/users/me/gifs/{gif_id}/tags", json=["new"]
        )
        assert response.status_code == 204

    async def test_replace_tags_on_nonexistent_gif_returns_404(self, web_client: AsyncClient):
        response = await web_client.put(
            "/api/v1/web/users/me/gifs/999999999/tags", json=["tag"]
        )
        assert response.status_code == 404

    async def test_delete_own_gif(self, web_client: AsyncClient):
        upload = await web_client.post(
            "/api/v1/web/users/me/gifs/new",
            files={"file": ("test.gif", GIF_BYTES, "image/gif")},
            data={"tags": ["tag"]},
        )
        gif_id = upload.json()["id"]

        response = await web_client.request(
            "DELETE", "/api/v1/web/users/me/gifs", params={"gif_ids": [gif_id]}
        )
        assert response.status_code == 200
        assert response.json() == 1


class TestDeleteAccount:

    async def test_delete_account_succeeds(self, web_client: AsyncClient):
        response = await web_client.delete("/api/v1/web/users/me")
        assert response.status_code == 204

    async def test_token_no_longer_works_after_account_deletion(self, web_client: AsyncClient):
        await web_client.delete("/api/v1/web/users/me")

        response = await web_client.get("/api/v1/web/users/me")
        assert response.status_code == 401
