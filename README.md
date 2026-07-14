# API

### 🔹 Описание
Полностью асинхронный API на Python с использованием FastAPI, PostgreSQL и Redis, предоставляющий удобный и расширяемый интерфейс для работы с данными через HTTP-запросы.  

### ✨ Основные возможности
- Быстрый запуск через [Docker](#-запуск-через-docker) или локально с [Python](#-запуск-через-python)  
- Управление схемой базы данных через Alembic миграции
- Тестирование с помощью pytest  
- Взаимодействие через [Telegram-бота](https://github.com/EgorBP/TgGifBot)
  
### 📦 Структура проекта

- **`app/`** — основной код приложения
- **`alembic/`** — миграции базы данных
- **`tests/`** — модульные тесты
- **`.env.example`** — пример конфигурационного файла для локального запуска
- **`.env.docker.example`** — пример конфигурационного файла для Docker
- **`Dockerfile`** — инструкции для создания Docker-образа
- **`docker-compose.yml`** — конфигурация контейнеров для развёртывания
- **`docker-compose.dev.yml`** — конфигурация для локальной разработки
- **`pyproject.toml` + `uv.lock`** — зависимости проекта

## ⚙️ Установка и запуск

1. Клонируйте репозиторий:
```bash
git clone https://github.com/EgorBP/API.git
cd API
```
2. Настройте переменные среды:
```bash
cp .env.docker.example .env.docker
cp .env.example .env
```

### 🐳 Запуск через Docker (Рекомендуется)
1. Соберите и запустите контейнеры:
```bash
docker compose up --build
```
2. API будет доступен по адресу:
[`http://127.0.0.1:8000`](http://127.0.0.1:8000)
> Документация доступна через Swagger UI: [`http://127.0.0.1:8000/docs`](http://127.0.0.1:8000/docs)  
> Или через ReDoc: [`http://127.0.0.1:8000/redoc`](http://127.0.0.1:8000/redoc)

### 🐍 Запуск через Python (UV)
1. Измените значения полей в `.env` на данные вашего реального адреса БД и Redis.
2. Установите зависимости:
```bash
uv sync --frozen
```
3. Выполните миграции:
```bash
uv run alembic upgrade head
```
4. Запустите приложение:
```bash
uv run uvicorn app.main:app --reload
```
5. API будет доступен по адресу:
[`http://127.0.0.1:8000`](http://127.0.0.1:8000)
> Документация доступна через Swagger UI: [`http://127.0.0.1:8000/docs`](http://127.0.0.1:8000/docs)  
> Или через ReDoc: [`http://127.0.0.1:8000/redoc`](http://127.0.0.1:8000/redoc)

## 🧪 Тестирование

Проект содержит **46 тестов** (integration, unit, database). Тестам нужны отдельные PostgreSQL и Redis (изолированы от dev/prod данных).

### Запуск тестов (рекомендуется — Docker Compose)

Самый простой способ — поднять всё окружение для тестов одной командой:
```bash
docker compose -f docker-compose.test.yml up --build --abort-on-container-exit
```
Это поднимет отдельные контейнеры PostgreSQL (`test_pet_project`) и Redis, смонтирует `tests/` в контейнер и запустит `pytest`.

Подробная документация и альтернативные варианты (локальный запуск без Docker): [TESTING.md](TESTING.md)
