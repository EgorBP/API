# 🚀 Async FastAPI Service

[![CI Pipeline](https://github.com/EgorBP/API/actions/workflows/ci.yml/badge.svg)](https://github.com/EgorBP/API/actions/workflows/ci.yml)

### 🔹 Описание
Асинхронное REST API на Python с использованием **FastAPI**, **PostgreSQL** и **Redis**. Сервис предоставляет расширяемый интерфейс для работы с данными, поддерживает кэширование, строгую типизацию и полное покрытие интеграционными и юниты-тестами.

---

### 🛠 Стек технологий

- **Language:** Python 3.13
- **Framework:** FastAPI, Pydantic v2
- **Database & ORM:** PostgreSQL, Async SQLAlchemy 2.0, Alembic
- **Caching:** Redis
- **Package Manager:** `uv`
- **Testing:** pytest, Testcontainers
- **CI/CD & DevOps:** GitHub Actions, Docker, Docker Compose

---

### ✨ Основные возможности

- 🏗 **Чистая архитектура:** Слоистая структура (`Routers` ➔ `Services` ➔ `Repositories`) для полной изоляции бизнес-логики и лёгкого тестирования.
- 👥 **Мульти-клиентский API:** Раздельные роутеры с изолированной логикой для веб-интерфейса (`/web`) и [Telegram-бота](https://github.com/EgorBP/TgGifBot) (`/bot`).
- 🔐 **Безопасность:** Авторизация бота по `X-Secret-Key` и JWT-авторизация пользователей с поддержкой ротации Refresh-токенов (Refresh Token Rotation).
- 📁 **Работа с файлами & Storage:** Выделенный сервис хранилища (`app/services/storage.py`) для валидации, обработки и управления загрузкой медиафайлов.
- ⚡ **Асинхронные фоновые задачи:** Выполнение ресурсоёмких процессов в фоновом режиме (`app/tasks/`).
- 📄 **Гибкая работа с данными:** Встроенная курсорная пагинация, фильтрация и сортировка для всех основных списков.
- 🧠 Redis-кэширование: Кэширование GET-запросов с инвалидацией после изменения данных.
- 🗄 **Управление БД:** Безопасное версионирование и контроль схемы базы данных через миграции Alembic.
- 🪵 **Структурированное логирование:** Кастомный формат логов с автоматическим парсингом данных в удобный формат. 
- 🛡 **Централизованная обработка ошибок:** Кастомные Exception Handlers с единым стандартизированным форматом ответов.
- 🛠 **Современный Toolchain:** Молниеносная сборка проекта и менеджмент зависимостей через `uv`.
- 🧪 **Автоматизированное тестирование:** 168 асинхронных тестов с `testcontainers` (автоматический запуск изолированных Postgres & Redis в Docker во время прогона `pytest`).

### 📦 Структура проекта

```text
├── alembic/                # Скрипты и миграции базы данных
├── app/                    # Основной код приложения
│   ├── api/                # Эндпоинты, middleware, зависимости и handlers
│   │   └── v1/routers/     # Маршруты API (раздельно для web/ и bot/)
│   ├── core/               # Настройки (Pydantic Settings), DB, Redis, Lifespan
│   ├── repositories/       # Слой работы с БД (SQLAlchemy)
│   ├── services/           # Бизнес-логика приложения
│   ├── tasks/              # Асинхронные фоновые задачи
│   └── utils/              # Хелперы для Auth, Redis и SQLAlchemy
├── envs/                   # Файлы окружения (.env)
├── tests/                  # Тестовый suite (unit, integration, repos, services)
├── .github/workflows/      # CI пайплайны GitHub Actions
├── Dockerfile              # Сборка образа приложения
├── docker-compose.yml      # Развёртывание (App + Postgres + Redis + Nginx)
├── nginx.conf              # Конфигурация Nginx Reverse Proxy
└── pyproject.toml          # Зависимости проекта
```

---

## ⚙️ Быстрый запуск

### 1. Клонирование и настройка окружения
```bash
git clone https://github.com/EgorBP/API.git
cd API
````
```bash
cp envs/.env.example envs/.env
cp envs/.env.docker.example envs/.env.docker
```


### 2. 🐳 Docker Compose
```bash
docker compose up --build
```
> Доступ к API: [`http://127.0.0.1:8000`](http://127.0.0.1:8000)    
> Сохраненные GIF: [`http://127.0.0.1/media/gifs/gif_filename`](http://127.0.0.1/media/gifs/) 
> 
> Swagger UI: [`http://127.0.0.1:8000/docs`](http://127.0.0.1:8000/docs)    
> ReDoc: [`http://127.0.0.1:8000/redoc`](http://127.0.0.1:8000/redoc)   


## 🧪 Тестирование

Проект содержит **168+ асинхронных тестов** (Unit, Integration, Repositories). Необходим Docker.

```bash
uv run pytest
```

> Благодаря `testcontainers` нужные контейнеры поднимаются и останавливаются автоматически.
