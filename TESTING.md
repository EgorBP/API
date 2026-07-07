# Testing Guide

## Обзор

Проект содержит комплексный набор тестов:
- **Integration тесты** (`tests/test_api.py`) — тестируют API endpoints через HTTP клиент
- **Unit тесты** (`tests/test_crud.py`) — тестируют CRUD операции на уровне базы данных
- **Database тесты** (`tests/test_db.py`) — проверяют структуру и подключение к БД

Всего: **34 теста** покрывающих основные сценарии работы API.

## Требования

- Python 3.13+
- PostgreSQL 17
- Установленные зависимости из `pyproject.toml`

## Настройка тестовой базы данных

Тесты используют отдельную тестовую БД с префиксом `test_`.

### Вариант 1: Локальный PostgreSQL

1. Убедитесь, что PostgreSQL запущен локально
2. Создайте тестовую базу данных:

```bash
psql -U postgres -c "CREATE DATABASE test_pet_project;"
```

3. Убедитесь, что `.env` файл содержит корректные настройки:

```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_DB=pet_project
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

Тесты автоматически добавят префикс `test_` к имени БД.

### Вариант 2: Docker Compose для разработки (рекомендуется)

Используйте отдельный `docker-compose.dev.yml` для локальной разработки:

1. Запустите PostgreSQL через Docker:

```bash
docker compose -f docker-compose.dev.yml up -d
```

2. Создайте тестовую базу данных:

```bash
docker compose -f docker-compose.dev.yml exec db psql -U postgres -c "CREATE DATABASE test_pet_project;"
```

3. Для остановки:

```bash
docker compose -f docker-compose.dev.yml down
```

**Примечание:** `docker-compose.dev.yml` пробрасывает порт 5432 наружу для локальной разработки. Основной `docker-compose.yml` не пробрасывает порты БД для безопасности в production.

## Запуск тестов

### Запустить все тесты

```bash
uv run pytest tests/ -v
```

### Запустить конкретный файл с тестами

```bash
# Integration тесты API
uv run pytest tests/test_api.py -v

# Unit тесты CRUD
uv run pytest tests/test_crud.py -v

# Тесты базы данных
uv run pytest tests/test_db.py -v
```

### Запустить конкретный тест

```bash
uv run pytest tests/test_api.py::TestUserEndpoints::test_create_and_get_gif -v
```

### Запустить с покрытием кода

```bash
uv run pytest tests/ --cov=app --cov-report=html
```

## Структура тестов

### Integration тесты (`test_api.py`)

**TestUserEndpoints** — тесты endpoints для работы с пользователями и GIF:
- `test_create_and_get_gif` — создание и получение GIF
- `test_update_gif_tags` — обновление тегов
- `test_get_nonexistent_gif` — обработка 404
- `test_delete_gif_tags` — удаление тегов
- `test_get_user_tags` — получение всех тегов пользователя
- `test_get_tags_for_nonexistent_user` — обработка несуществующего пользователя

**TestSearchEndpoint** — тесты поиска GIF:
- `test_search_without_tags` — поиск без фильтров
- `test_search_with_single_tag` — поиск по одному тегу
- `test_search_with_multiple_tags` — поиск по нескольким тегам (AND логика)
- `test_search_with_no_matches` — поиск без результатов
- `test_search_for_nonexistent_user` — поиск для несуществующего пользователя

**TestEdgeCases** — граничные случаи:
- `test_empty_tags_list` — пустой список тегов
- `test_duplicate_tags` — дублирующиеся теги
- `test_multiple_users_isolation` — изоляция данных между пользователями

### Unit тесты (`test_crud.py`)

**TestUsersCRUD** — тесты CRUD операций для пользователей:
- Создание пользователя
- Обработка дубликатов
- Получение по tg_id
- Удаление

**TestGifsCRUD** — тесты CRUD операций для GIF:
- Создание GIF
- Обработка дубликатов
- Поиск по tg_gif_id
- Удаление

**TestTagsCRUD** — тесты CRUD операций для тегов:
- Создание тега
- Обработка дубликатов
- Получение нескольких тегов

**TestUserGifTagCRUD** — тесты связей пользователь-GIF-тег:
- Создание связи
- Обработка дубликатов
- Удаление связи
- Каскадное удаление

### Database тесты (`test_db.py`)

- `test_db_connect` — проверка подключения
- `test_db_tables_exist` — проверка существования таблиц
- `test_db_user_table_structure` — структура таблицы users
- `test_db_gif_table_structure` — структура таблицы gifs
- `test_db_foreign_keys` — проверка внешних ключей

## Фикстуры

Все фикстуры определены в `tests/conftest.py`:

- `test_engine` — async engine для тестовой БД (создаётся для каждого теста)
- `db_session` — async сессия БД (изолированная для каждого теста)
- `client` — async HTTP клиент для тестирования API

## Изоляция тестов

Каждый тест работает с чистой БД:
1. Перед тестом создаются все таблицы
2. После теста все таблицы удаляются
3. Транзакции откатываются после каждого теста

Это гарантирует полную изоляцию и отсутствие влияния тестов друг на друга.

## Troubleshooting

### ConnectionRefusedError

Если видите ошибку `ConnectionRefusedError`, значит PostgreSQL не запущен или недоступен:

```bash
# Проверьте статус PostgreSQL
docker compose ps

# Или для локального PostgreSQL
pg_isready -h localhost -p 5432
```

### Тестовая БД не существует

```bash
# Создайте тестовую БД
docker compose exec db psql -U postgres -c "CREATE DATABASE test_pet_project;"
```

### Ошибки миграций

Если структура БД не соответствует моделям:

```bash
# Пересоздайте тестовую БД
docker compose exec db psql -U postgres -c "DROP DATABASE IF EXISTS test_pet_project;"
docker compose exec db psql -U postgres -c "CREATE DATABASE test_pet_project;"
```

Тесты автоматически создадут нужную структуру.

## CI/CD

Для запуска тестов в CI используйте PostgreSQL service:

```yaml
services:
  postgres:
    image: postgres:17
    env:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: pet_project
    ports:
      - 5432:5432
```

Затем запустите тесты:

```bash
uv run pytest tests/ -v
```
