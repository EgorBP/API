import time
import logging
from starlette.types import ASGIApp, Scope, Receive, Send
from starlette.responses import JSONResponse


class ASGIRequestLoggingMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app
        self.access_logger = logging.getLogger("app.access")
        self.error_logger = logging.getLogger("app.api.exceptions")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.perf_counter()

        client = scope.get("client")
        host = client[0] if client else "-"
        port = client[1] if client else "-"
        method = scope["method"]
        path = scope["path"]

        query_string = scope.get("query_string", b"").decode("utf-8")
        path = f"{path}?{query_string}" if query_string else path
        
        response_started = False
        status_code = 500

        async def send_wrapper(message):
            nonlocal status_code, response_started
            if message["type"] == "http.response.start":
                response_started = True
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000

            # 1. Пишем один подробный трейсбэк в наш логгер ошибок
            self.error_logger.exception(
                "Unhandled exception caught in middleware on %s %s: %s",
                method, path, exc
            )

            # 2. Пишем стандартную строку access-лога
            self.access_logger.info(
                '%s:%s - "%s %s HTTP/1.1" 500 Internal Server Error %.2fms',
                host, port, method, path, duration_ms
            )

            # 3. Безопасно отвечаем клиенту
            if not response_started:
                # Если заголовки еще не отправлялись — отдаем красивый JSON
                response = JSONResponse(
                    status_code=500,
                    content={"detail": "Unexpected internal server error."}
                )
                await response(scope, receive, send)
            else:
                # Если ответ уже начал стримиться клиенту, мы не можем отправить JSONResponse.
                # Придется пробросить ошибку выше, чтобы Uvicorn аварийно закрыл соединение.
                raise
        else:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self.access_logger.info(
                '%s:%s - "%s %s HTTP/1.1" %s %.2fms',
                host, port, method, path, status_code, duration_ms
            )
