"""Tests for the bot-facing API (`/api/v1/bot/users/{tg_user_id}/...`),
guarded by the shared `X-Secret-Key` header.
"""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers import GIF_BYTES, MP4_BYTES


class TestUploadNewGif:

    async def test_upload_valid_gif_creates_it_with_tags(self, bot_client: AsyncClient):
        response = await bot_client.post(
            "/api/v1/bot/users/100001/gifs/new",
            files={"file": ("test.gif", GIF_BYTES, "image/gif")},
            data={"tags": ["cat", "funny"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert set(data["tags"]) == {"cat", "funny"}
        assert "id" in data

    async def test_upload_valid_mp4_is_accepted(self, bot_client: AsyncClient):
        response = await bot_client.post(
            "/api/v1/bot/users/100002/gifs/new",
            files={"file": ("test.mp4", MP4_BYTES, "video/mp4")},
            data={"tags": ["video"]},
        )
        assert response.status_code == 200

    async def test_upload_rejects_wrong_mime_type(self, bot_client: AsyncClient):
        response = await bot_client.post(
            "/api/v1/bot/users/100003/gifs/new",
            files={"file": ("test.png", b"\x89PNG\r\n\x1a\n", "image/png")},
            data={"tags": ["cat"]},
        )
        assert response.status_code == 400

    async def test_upload_rejects_spoofed_content_with_correct_mime_type(self, bot_client: AsyncClient):
        response = await bot_client.post(
            "/api/v1/bot/users/100004/gifs/new",
            files={"file": ("fake.gif", b"not actually a gif", "image/gif")},
            data={"tags": ["cat"]},
        )
        assert response.status_code == 400

    async def test_upload_requires_at_least_one_tag(self, bot_client: AsyncClient):
        response = await bot_client.post(
            "/api/v1/bot/users/100005/gifs/new",
            files={"file": ("test.gif", GIF_BYTES, "image/gif")},
            data={},
        )
        assert response.status_code == 422

    async def test_upload_reuses_gif_content_across_users(self, bot_client: AsyncClient):
        first = await bot_client.post(
            "/api/v1/bot/users/100006/gifs/new",
            files={"file": ("shared.gif", GIF_BYTES + b"unique_marker", "image/gif")},
            data={"tags": ["first"]},
        )
        second = await bot_client.post(
            "/api/v1/bot/users/100007/gifs/new",
            files={"file": ("shared.gif", GIF_BYTES + b"unique_marker", "image/gif")},
            data={"tags": ["second"]},
        )
        assert first.json()["id"] == second.json()["id"]

    async def test_upload_creates_bot_user_on_first_contact(self, bot_client: AsyncClient):
        response = await bot_client.post(
            "/api/v1/bot/users/100008/gifs/new",
            files={"file": ("test.gif", GIF_BYTES, "image/gif")},
            data={"tags": ["new_user_tag"]},
        )
        assert response.status_code == 200

        count_response = await bot_client.get("/api/v1/bot/users/100008/gifs/count")
        assert count_response.json() == 1


class TestGetUserGifs:

    async def test_returns_empty_page_for_new_user(self, bot_client: AsyncClient):
        response = await bot_client.get("/api/v1/bot/users/100101/gifs")
        assert response.status_code == 200
        assert response.json()["data"] == []

    async def test_lists_uploaded_gifs_with_tags(self, bot_client: AsyncClient):
        await bot_client.post(
            "/api/v1/bot/users/100102/gifs/new",
            files={"file": ("test.gif", GIF_BYTES, "image/gif")},
            data={"tags": ["cat", "cute"]},
        )

        response = await bot_client.get("/api/v1/bot/users/100102/gifs")
        data = response.json()["data"]
        assert len(data) == 1
        assert set(data[0]["tags"]) == {"cat", "cute"}

    async def test_filters_by_tags(self, bot_client: AsyncClient):
        await bot_client.post(
            "/api/v1/bot/users/100103/gifs/new",
            files={"file": ("a.gif", GIF_BYTES + b"a", "image/gif")},
            data={"tags": ["cat"]},
        )
        await bot_client.post(
            "/api/v1/bot/users/100103/gifs/new",
            files={"file": ("b.gif", GIF_BYTES + b"b", "image/gif")},
            data={"tags": ["dog"]},
        )

        response = await bot_client.get("/api/v1/bot/users/100103/gifs", params={"tags": ["cat"]})
        data = response.json()["data"]
        assert len(data) == 1
        assert "cat" in data[0]["tags"]


class TestGetUserTags:

    async def test_returns_all_distinct_tags(self, bot_client: AsyncClient):
        await bot_client.post(
            "/api/v1/bot/users/100201/gifs/new",
            files={"file": ("a.gif", GIF_BYTES + b"a", "image/gif")},
            data={"tags": ["one", "two"]},
        )
        await bot_client.post(
            "/api/v1/bot/users/100201/gifs/new",
            files={"file": ("b.gif", GIF_BYTES + b"b", "image/gif")},
            data={"tags": ["two", "three"]},
        )

        response = await bot_client.get("/api/v1/bot/users/100201/tags/all")
        assert set(response.json()["tags"]) == {"one", "two", "three"}

    async def test_returns_empty_for_user_without_gifs(self, bot_client: AsyncClient):
        response = await bot_client.get("/api/v1/bot/users/100202/tags/all")
        assert response.json()["tags"] == []


class TestUpdateGifTags:

    async def test_replaces_full_tag_set(self, bot_client: AsyncClient):
        upload = await bot_client.post(
            "/api/v1/bot/users/100301/gifs/new",
            files={"file": ("test.gif", GIF_BYTES, "image/gif")},
            data={"tags": ["old"]},
        )
        gif_id = upload.json()["id"]

        response = await bot_client.put(
            f"/api/v1/bot/users/100301/gifs/{gif_id}/tags",
            json=["new", "tags"],
        )
        assert response.status_code == 204

        gifs = await bot_client.get("/api/v1/bot/users/100301/gifs")
        updated = next(g for g in gifs.json()["data"] if g["id"] == gif_id)
        assert set(updated["tags"]) == {"new", "tags"}

    async def test_returns_404_for_nonexistent_gif(self, bot_client: AsyncClient):
        response = await bot_client.put(
            "/api/v1/bot/users/100302/gifs/999999999/tags",
            json=["tag"],
        )
        assert response.status_code == 404

    async def test_requires_at_least_one_tag(self, bot_client: AsyncClient):
        upload = await bot_client.post(
            "/api/v1/bot/users/100303/gifs/new",
            files={"file": ("test.gif", GIF_BYTES, "image/gif")},
            data={"tags": ["old"]},
        )
        gif_id = upload.json()["id"]

        response = await bot_client.put(
            f"/api/v1/bot/users/100303/gifs/{gif_id}/tags",
            json=[],
        )
        assert response.status_code == 422


class TestDeleteUserGif:

    async def test_removes_gif_from_library(self, bot_client: AsyncClient):
        upload = await bot_client.post(
            "/api/v1/bot/users/100401/gifs/new",
            files={"file": ("test.gif", GIF_BYTES, "image/gif")},
            data={"tags": ["tag"]},
        )
        gif_id = upload.json()["id"]

        response = await bot_client.delete(
            "/api/v1/bot/users/100401/gifs", params={"gif_ids": [gif_id]}
        )
        assert response.status_code == 200
        assert response.json() == 1

        count = await bot_client.get("/api/v1/bot/users/100401/gifs/count")
        assert count.json() == 0

    async def test_returns_404_when_nothing_deleted(self, bot_client: AsyncClient):
        response = await bot_client.delete(
            "/api/v1/bot/users/100402/gifs", params={"gif_ids": [999999999]}
        )
        assert response.status_code == 404

    async def test_does_not_affect_other_users(self, bot_client: AsyncClient):
        upload = await bot_client.post(
            "/api/v1/bot/users/100403/gifs/new",
            files={"file": ("shared.gif", GIF_BYTES + b"shared_marker", "image/gif")},
            data={"tags": ["tag"]},
        )
        await bot_client.post(
            "/api/v1/bot/users/100404/gifs/new",
            files={"file": ("shared.gif", GIF_BYTES + b"shared_marker", "image/gif")},
            data={"tags": ["tag"]},
        )
        gif_id = upload.json()["id"]

        await bot_client.delete("/api/v1/bot/users/100403/gifs", params={"gif_ids": [gif_id]})

        other_count = await bot_client.get("/api/v1/bot/users/100404/gifs/count")
        assert other_count.json() == 1
