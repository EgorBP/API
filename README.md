# API

### 🔹 Описание
RESTful API на Python с использованием FastAPI, предоставляющее удобный и расширяемый интерфейс для работы с данными через HTTP-запросы.  
> Вы можете протестировать уже развернутое [API](https://api-production-8e0b.up.railway.app/docs) и [Бота](https://t.me/GifRepositoryBot).

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
- **`pyproject.toml`** — зависимости проекта (управляется через uv)

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

### 🐳 Запуск через Docker
1. Соберите и запустите контейнеры:
```bash
docker compose up --build
```
2. API будет доступен по адресу:
[`http://127.0.0.1:8000`](http://127.0.0.1:8000)
> Документация доступна через Swagger UI: [`http://127.0.0.1:8000/docs`](http://127.0.0.1:8000/docs)  
> Или через ReDoc: [`http://127.0.0.1:8000/redoc`](http://127.0.0.1:8000/redoc)

### 🐍 Запуск через Python
1. Измените *`DATABASE_URL`* в `.env` на ваш реальный адрес БД.
2. Создайте виртуальное окружение и активируйте его:
```python
python -m venv .venv
```
##### Для Windows
```bash
.venv\Scripts\activate
```
##### Для Linux/macOS
```bash
source .venv/bin/activate
```
3. Установите зависимости:
```bash
uv sync
```
Или через pip:
```bash
pip install -e .
```
4. Выполните миграции:
```bash
alembic upgrade head
```
5. Запустите приложение:
```bash
uv run uvicorn app.main:app --reload
```
6. API будет доступен по адресу:
[`http://127.0.0.1:8000`](http://127.0.0.1:8000)
> Документация доступна через Swagger UI: [`http://127.0.0.1:8000/docs`](http://127.0.0.1:8000/docs)  
> Или через ReDoc: [`http://127.0.0.1:8000/redoc`](http://127.0.0.1:8000/redoc)

## 🧪 Тестирование

Проект содержит **34 теста** (integration, unit, database).

### Запуск тестов

1. Запустите PostgreSQL для разработки:
```bash
docker compose -f docker-compose.dev.yml up -d
```

2. Создайте тестовую базу данных:
```bash
docker compose -f docker-compose.dev.yml exec db psql -U postgres -c "CREATE DATABASE test_pet_project;"
```

3. Запустите тесты:
```bash
uv run pytest tests/ -v
```

Подробная документация по тестированию: [TESTING.md](TESTING.md)
