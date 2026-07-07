# Docker Compose для разработки

Этот файл предназначен **только для локальной разработки и тестирования**.

## Отличия от docker-compose.yml

- **`docker-compose.yml`** — для production, порты БД не пробрасываются наружу
- **`docker-compose.dev.yml`** — для разработки, порт 5432 доступен на localhost

## Использование

### Запуск

```bash
docker compose -f docker-compose.dev.yml up -d
```

### Создание тестовой БД

```bash
docker compose -f docker-compose.dev.yml exec db psql -U postgres -c "CREATE DATABASE test_pet_project;"
```

### Остановка

```bash
docker compose -f docker-compose.dev.yml down
```

### Полная очистка (включая данные)

```bash
docker compose -f docker-compose.dev.yml down -v
```

## Подключение к БД

После запуска PostgreSQL доступен на:
- **Host:** localhost
- **Port:** 5432
- **User:** postgres
- **Password:** 123465 (из `.env`)
- **Database:** pet_project

## Запуск тестов

После запуска dev-контейнера:

```bash
uv run pytest tests/ -v
```

## Безопасность

⚠️ **Не используйте этот файл в production!** Проброс порта БД наружу — это риск безопасности.
