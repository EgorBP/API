# 🚀 Async FastAPI Service

[![CI Pipeline](https://github.com/EgorBP/API/actions/workflows/ci.yml/badge.svg)](https://github.com/EgorBP/API/actions/workflows/ci.yml)

### 🔹 Описание
Асинхронное REST API, построенное на **FastAPI**, **PostgreSQL** и **Redis**. Проект демонстрирует современный подход к разработке backend-приложений: слоистую архитектуру, JWT-аутентификацию, Redis-кэширование, асинхронную обработку задач, автоматизированное тестирование и CI.

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

- 🏗 **Слоистая архитектура:** Разделение на `Routers` → `Services` → `Repositories`, обеспечивающее изоляцию бизнес-логики, низкую связанность компонентов и удобство тестирования.
- 👥 **Мульти-клиентский API:** Независимые роутеры для веб-клиента (`/web`) и [Telegram-бота](https://github.com/EgorBP/TgGifBot) (`/bot`) с общей бизнес-логикой и отдельными механизмами авторизации.
- 🔐 **Аутентификация и авторизация:** JWT Access/Refresh Tokens с поддержкой **Refresh Token Rotation**, а также авторизация Telegram-бота через `X-Secret-Key`.
- 📁 **Работа с файлами:** Выделенный сервис хранения для загрузки, валидации, обработки и управления медиафайлами.
- ⚡ **Фоновые задачи:** Выполнение ресурсоёмких операций в асинхронном режиме без блокировки обработки HTTP-запросов.
- 📄 **Работа со списками данных:** Поддержка курсорной пагинации, фильтрации и сортировки для основных сущностей API.
- 🧠 **Redis-кэширование:** Кэширование GET-запросов с автоматической инвалидацией при изменении данных.
- 🗄 **Миграции базы данных:** Версионирование схемы PostgreSQL с помощью Alembic.
- 🪵 **Структурированное логирование:** Единый формат логов для удобной диагностики и анализа работы приложения.
- 🛡 **Обработка ошибок:** Централизованные Exception Handlers с единым форматом ответов API.
- 🛠 **Современный toolchain:** Управление зависимостями через `uv`, контейнеризация с Docker и автоматическая проверка проекта в GitHub Actions.
- 🧪 **Автоматизированное тестирование:** 173 асинхронных теста (Unit, Integration, Repository) с использованием `testcontainers`, автоматически поднимающих изолированные экземпляры PostgreSQL и Redis во время выполнения `pytest`.
 
### 📦 Структура проекта

```text
├── alembic/                # Миграции базы данных
├── app/                    # Основной код приложения
│   ├── api/                # Эндпоинты, middleware, зависимости и handlers
│   │   └── v1/routers/     # Маршруты API (web/, bot/, dev/ и глобальные пути)
│   ├── core/               # Настройки (Pydantic Settings), DB, Redis, Lifespan
│   ├── repositories/       # Слой работы с БД (SQLAlchemy)
│   ├── services/           # Бизнес-логика приложения
│   ├── tasks/              # Асинхронные фоновые задачи
│   └── utils/              # Хелперы для Auth, Redis и SQLAlchemy
├── envs/                   # Файлы окружения (.env)
├── tests/                  # Тестовый suite (unit, integration, repos, services)
├── .github/workflows/      # CI пайплайны GitHub Actions
├── Dockerfile              # Сборка образа приложения
├── docker-compose.yml      # Развёртывание (Postgres + Redis → Migration → App → Nginx)
├── nginx.conf              # Конфигурация Nginx Reverse Proxy
└── pyproject.toml          # Зависимости проекта
```

---

## ⚙️ Запуск приложения

### 1. Клонирование проекта
```bash
git clone https://github.com/EgorBP/API.git
cd API
````

### 2. Настройка окружения
```bash
cp envs/.env.example envs/.env
cp envs/.env.docker.example envs/.env.docker
```
> DEV_MODE позволяет создавать JWT токены через отдельный эндпоинт для любого Telegram ID пользователя.   
> Для тестов DEV_MODE всегда false.
> 
> Для использования настоящей аутентификации через Telegram создайте своего бота в [@BotFather](https://telegram.me/BotFather), замените BOT_TOKEN на ваш токен и задайте адрес вашего сайта в [@BotFather](https://telegram.me/BotFather) → Login Widget.

### 3. 🐳 Docker Compose
```bash
docker compose up --build
```
> Доступ к API: [`http://127.0.0.1:8000`](http://127.0.0.1:8000)    
> Сохраненные GIF: [`http://127.0.0.1/media/gifs/gif_filename`](http://127.0.0.1/media/gifs/) 
> 
> Swagger UI: [`http://127.0.0.1:8000/docs`](http://127.0.0.1:8000/docs)    
> ReDoc: [`http://127.0.0.1:8000/redoc`](http://127.0.0.1:8000/redoc)   


## 🧪 Тестирование

Проект содержит **173 асинхронных теста** (Unit, Integration, Repositories).   
Для запуска необходим работающий Docker.

```bash
uv run pytest
```

> Благодаря `testcontainers` нужные контейнеры поднимаются и останавливаются автоматически.
