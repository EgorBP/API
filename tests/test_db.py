from app.database import SessionLocal
from sqlalchemy import text


def test_db_connect():
    with SessionLocal() as session:
        assert session.execute(text("SELECT 1")).scalar() == 1


def test_db_tables_exist():
    with SessionLocal() as session:
        result = session.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
        ).fetchall()
    assert result == [('alembic_version',), ('gifs',), ('user_gif_tags',), ('tags',), ('users',)]
