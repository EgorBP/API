FROM python:3.13-slim
LABEL authors="Egor"

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen

COPY alembic.ini .
COPY alembic/ ./alembic/
COPY app/ ./app/

CMD uv run alembic upgrade head && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
