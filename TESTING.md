# Testing Guide

Тесты:
- `tests/test_api.py` — API (integration)
- `tests/test_crud.py` — CRUD-операции (unit)
- `tests/test_db.py` — структура БД
- `tests/test_auth.py` — авторизация
- `tests/test_exceptions.py` — обработчики ошибок
- `tests/test_caching.py` — кэширование

Всего 46 тестов.

## Запуск (рекомендуется)

```bash
docker compose -f docker-compose.test.yml up --build --abort-on-container-exit
```


## Тестовое окружение

`docker-compose.test.yml` запускает:

- PostgreSQL — отдельный контейнер для тестов
- Redis — отдельный контейнер для тестов
- test runner — контейнер с pytest

Тесты используют:
- PostgreSQL database: `test_<POSTGRES_DB>`
- Redis database: `15`


## Запуск без Docker

1. Локальный Postgres и Redis должны быть запущены, `.env` заполнен (см. `.env.example`).
2. Создать тестовую БД:
```bash
psql -U postgres -c "CREATE DATABASE test_pet_project;"
```
3. Запустить тесты:
```bash
uv run pytest tests/ -v
```

## Запуск отдельных модулей и тестов

```bash
# Только один файл
uv run pytest tests/test_api.py -v

# Конкретный класс
uv run pytest tests/test_api.py::TestUserEndpoints -v

# Конкретный тест
uv run pytest tests/test_api.py::TestUserEndpoints::test_create_and_get_gif -v
```
