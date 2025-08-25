FROM python:3.13-slim
LABEL authors="Egor"

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY alembic.ini .
COPY alembic/ ./alembic/
COPY app ./app/

CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000
