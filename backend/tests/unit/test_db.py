"""Sanity checks for the database schema created from the ORM models."""
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession


async def test_db_connect(db_session: AsyncSession):
    """The test database is reachable and can execute a trivial query."""
    result = await db_session.execute(text("SELECT 1"))
    assert result.scalar() == 1


async def test_db_tables_exist(db_session: AsyncSession):
    """All expected tables were created from the ORM models."""
    result = await db_session.execute(
        text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
    )
    actual_tables = {row[0] for row in result.fetchall()}

    expected_tables = {"users", "gifs", "tags", "user_gif_tags"}
    assert expected_tables.issubset(actual_tables), f"Missing tables: {expected_tables - actual_tables}"


async def test_db_users_table_structure(db_session: AsyncSession):
    """The `users` table has the expected columns and constraints."""
    result = await db_session.execute(
        text(
            "SELECT column_name, is_nullable FROM information_schema.columns "
            "WHERE table_name = 'users'"
        )
    )
    columns = {row[0]: row[1] for row in result.fetchall()}

    assert "id" in columns
    assert "tg_id" in columns
    assert columns["tg_id"] == "NO"


async def test_db_users_tg_id_is_unique(db_session: AsyncSession):
    """`users.tg_id` enforces unique constraint on duplicate insertion."""
    await db_session.execute(
        text("INSERT INTO users (tg_id) VALUES (:tg_id)"),
        {"tg_id": 12345},
    )
    await db_session.commit()

    with pytest.raises(IntegrityError):
        await db_session.execute(
            text("INSERT INTO users (tg_id) VALUES (:tg_id)"),
            {"tg_id": 12345},
        )
        await db_session.commit()
    

async def test_db_gifs_table_structure(db_session: AsyncSession):
    """The `gifs` table has the expected columns."""
    result = await db_session.execute(
        text(
            "SELECT column_name, is_nullable FROM information_schema.columns "
            "WHERE table_name = 'gifs'"
        )
    )
    columns = {row[0]: row[1] for row in result.fetchall()}

    assert "id" in columns
    assert "file_path" in columns
    assert "file_hash" in columns
    assert columns["file_path"] == "NO"
    assert columns["file_hash"] == "NO"


async def test_db_gifs_file_hash_and_path_are_unique(db_session: AsyncSession):
    """`gifs.file_path` and `gifs.file_hash` both have unique constraints."""
    result = await db_session.execute(
        text(
            "SELECT kcu.column_name FROM information_schema.table_constraints tc "
            "JOIN information_schema.key_column_usage kcu "
            "ON tc.constraint_name = kcu.constraint_name "
            "WHERE tc.table_name = 'gifs' AND tc.constraint_type = 'UNIQUE'"
        )
    )
    unique_columns = {row[0] for row in result.fetchall()}
    assert {"file_path", "file_hash"}.issubset(unique_columns)


async def test_db_tags_tag_is_unique(db_session: AsyncSession):
    """`tags.tag` enforces unique constraint on duplicate insertion."""
    await db_session.execute(
        text("INSERT INTO tags (tag) VALUES (:tag)"),
        {"tag": "funny"},
    )
    await db_session.commit()

    with pytest.raises(IntegrityError):
        await db_session.execute(
            text("INSERT INTO tags (tag) VALUES (:tag)"),
            {"tag": "funny"},
        )
        await db_session.commit()
        

async def test_db_user_gif_tags_foreign_keys(db_session: AsyncSession):
    """`user_gif_tags` has foreign keys to users, gifs, and tags."""
    result = await db_session.execute(
        text(
            "SELECT ccu.table_name FROM information_schema.table_constraints tc "
            "JOIN information_schema.key_column_usage kcu "
            "ON tc.constraint_name = kcu.constraint_name "
            "JOIN information_schema.constraint_column_usage ccu "
            "ON ccu.constraint_name = tc.constraint_name "
            "WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_name = 'user_gif_tags'"
        )
    )
    foreign_tables = {row[0] for row in result.fetchall()}
    assert foreign_tables == {"users", "gifs", "tags"}


async def test_db_user_gif_tags_composite_unique(db_session: AsyncSession):
    """`user_gif_tags` enforces uniqueness on (user_id, gif_id, tag_id)."""
    user_res = await db_session.execute(
        text("INSERT INTO users (tg_id) VALUES (:tg_id) RETURNING id"),
        {"tg_id": 999111},
    )
    user_id = user_res.scalar_one()

    gif_res = await db_session.execute(
        text(
            "INSERT INTO gifs (file_path, file_hash) "
            "VALUES (:file_path, :file_hash) RETURNING id"
        ),
        {
            "file_path": "media/test_unique.mp4",
            "file_hash": "a" * 64,
        },
    )
    gif_id = gif_res.scalar_one()

    tag_res = await db_session.execute(
        text("INSERT INTO tags (tag) VALUES (:tag) RETURNING id"),
        {"tag": "composite_unique_test_tag"},
    )
    tag_id = tag_res.scalar_one()

    await db_session.commit()

    await db_session.execute(
        text(
            "INSERT INTO user_gif_tags (user_id, gif_id, tag_id) "
            "VALUES (:user_id, :gif_id, :tag_id)"
        ),
        {"user_id": user_id, "gif_id": gif_id, "tag_id": tag_id},
    )
    await db_session.commit()

    with pytest.raises(IntegrityError):
        await db_session.execute(
            text(
                "INSERT INTO user_gif_tags (user_id, gif_id, tag_id) "
                "VALUES (:user_id, :gif_id, :tag_id)"
            ),
            {"user_id": user_id, "gif_id": gif_id, "tag_id": tag_id},
        )
        await db_session.commit()
