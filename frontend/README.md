# GIFs API Frontend

Небольшой React/Vite demo UI для возможностей API: public GIF search, popular cache endpoints, Telegram/JWT web flow, личная библиотека, upload GIF/MP4, replace tags, unlink/delete.

## Env

```env
VITE_API_BASE_URL=/api
VITE_MEDIA_BASE_URL=
VITE_DEV_MODE=false
VITE_DEV_AUTH_ENDPOINT=/v1/dev/auth/{tg_user_id}
VITE_TELEGRAM_BOT_USERNAME=
```

В dev-mode Telegram-кнопка заменяется на поле `tg_user_id` и вызывает:

```http
POST /api/v1/dev/auth/{tg_user_id}
```

## Docker Compose example

```yaml
services:
  api:
    build: .
    container_name: gifs-api
    expose:
      - "8000"

  frontend:
    build:
      context: ./frontend
      args:
        VITE_API_BASE_URL: /api
        VITE_MEDIA_BASE_URL: ""
        VITE_DEV_MODE: ${DEV_MODE}
        VITE_DEV_AUTH_ENDPOINT: /v1/dev/auth/{tg_user_id}
        VITE_TELEGRAM_BOT_USERNAME: ${TELEGRAM_BOT_USERNAME:-}
    ports:
      - "80:80"
    volumes:
      - ./media:/usr/share/nginx/html/media:ro
    depends_on:
      - api
```

`frontend/nginx.conf` уже проксирует `/api/` на `http://api:8000/api/` и отдает `/media/` из volume. Если сервис backend в compose называется иначе, поменяйте `proxy_pass`.

В текущем корневом `docker-compose.yml` уже есть сервис `nginx` на порту `80`. Для frontend есть два простых варианта:

1. заменить сервис `nginx` на сервис `frontend` из примера выше;
2. оставить старый `nginx`, но перенести в его конфиг содержимое `frontend/nginx.conf` и отдельно собирать/монтировать `frontend/dist`.
