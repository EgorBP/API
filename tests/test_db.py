import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def test_db_connect(db_session: AsyncSession):
    """Тест подключения к базе данных."""
    result = await db_session.execute(text("SELECT 1"))
    assert result.scalar() == 1


async def test_db_tables_exist(db_session: AsyncSession):
    """Тест проверки существования всех необходимых таблиц."""
    result = await db_session.execute(
        text("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name")
    )
    tables = [row[0] for row in result.fetchall()]
    
    # Проверяем наличие всех основных таблиц
    expected_tables = {'gifs', 'tags', 'user_gif_tags', 'users'}
    actual_tables = set(tables)
    
    assert expected_tables.issubset(actual_tables), f"Missing tables: {expected_tables - actual_tables}"


async def test_db_user_table_structure(db_session: AsyncSession):
    """Тест структуры таблицы users."""
    result = await db_session.execute(
        text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'users'
            ORDER BY ordinal_position
        """)
    )
    columns = {row[0]: {"type": row[1], "nullable": row[2]} for row in result.fetchall()}
    
    assert "id" in columns
    assert "tg_id" in columns
    assert columns["tg_id"]["nullable"] == "NO"


async def test_db_gif_table_structure(db_session: AsyncSession):
    """Тест структуры таблицы gifs."""
    result = await db_session.execute(
        text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'gifs'
            ORDER BY ordinal_position
        """)
    )
    columns = {row[0]: {"type": row[1], "nullable": row[2]} for row in result.fetchall()}
    
    assert "id" in columns
    assert "tg_gif_id" in columns
    assert columns["tg_gif_id"]["nullable"] == "NO"


async def test_db_foreign_keys(db_session: AsyncSession):
    """Тест наличия внешних ключей в таблице user_gif_tags."""
    result = await db_session.execute(
        text("""
            SELECT
                tc.constraint_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_name = 'user_gif_tags'
        """)
    )
    foreign_keys = result.fetchall()
    
    # Должно быть 3 внешних ключа: user_id, gif_id, tag_id
    assert len(foreign_keys) == 3
    
    foreign_tables = {row[2] for row in foreign_keys}
    assert foreign_tables == {'users', 'gifs', 'tags'}
