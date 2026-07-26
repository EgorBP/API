import time
import logging
from starlette.types import ASGIApp, Scope, Receive, Send
from starlette.responses import JSONResponse


class ASGIRequestLoggingMiddleware:
    """ASGI middleware that logs every request and safely handles unhandled errors.

    Logs a standard access-log line for every request (method, path,
    status, duration). If a handler raises an uncaught exception, also
    logs the full traceback separately and, if no response has been sent
    yet, returns a generic 500 JSON error instead of letting the
    connection crash silently.
    """
    
    def __init__(self, app: ASGIApp):
        """Initializes the middleware.

        Args:
            app: The next ASGI application in the stack.
        """
        self.app = app
        self.access_logger = logging.getLogger("app.access")
        self.error_logger = logging.getLogger("app.api.exceptions")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Handles one ASGI request, logging it and any unhandled error.

        Non-HTTP scopes (e.g. lifespan, websocket) are passed through
        untouched. For HTTP requests, wraps `send` to capture the
        response status code, then logs an access-log line after the
        request completes. If the downstream app raises, logs the
        traceback and returns a 500 JSON response — unless the response
        had already started streaming, in which case the exception is
        re-raised so the connection is aborted instead of sending
        malformed data.

        Args:
            scope: The ASGI connection scope.
            receive: Callable to receive ASGI events.
            send: Callable to send ASGI events.
        """
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
            """Wraps the ASGI send callable to capture status code and monitor response state."""
            nonlocal status_code, response_started
            if message["type"] == "http.response.start":
                response_started = True
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000

            # 1. Log one detailed traceback to our error logger
            self.error_logger.exception(
                "Unhandled exception caught in middleware on %s %s: %s",
                method, path, exc
            )

            # 2. Log a standard access-log line
            self.access_logger.info(
                '%s:%s - "%s %s HTTP/1.1" 500 Internal Server Error %.2fms',
                host, port, method, path, duration_ms
            )

            # 3. Safely respond to the client
            if not response_started:
                # If headers haven't been sent yet, return a clean JSON error
                response = JSONResponse(
                    status_code=500,
                    content={"detail": "Unexpected internal server error."}
                )
                await response(scope, receive, send)
            else:
                # If the response has already started streaming, we can't send a JSONResponse.
                # Re-raise so Uvicorn aborts the connection instead.
                raise
        else:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self.access_logger.info(
                '%s:%s - "%s %s HTTP/1.1" %s %.2fms',
                host, port, method, path, status_code, duration_ms
            )
