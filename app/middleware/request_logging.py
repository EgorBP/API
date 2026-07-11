import logging
import time
from http import HTTPStatus

from fastapi import Request


logger = logging.getLogger("app.access")


async def request_logging_middleware(
    request: Request,
    call_next,
):
    start = time.perf_counter()

    response = await call_next(request)

    duration_ms = (time.perf_counter() - start) * 1000

    client_host = request.client.host if request.client else "-"
    client_port = request.client.port if request.client else "-"

    status_text = HTTPStatus(response.status_code).phrase

    full_path = request.url.path
    if request.url.query:
        full_path = f"{full_path}?{request.url.query}"
        
    logger.info(
        '%s:%s - "%s %s HTTP/1.1" %s %s %.2fms',
        client_host,
        client_port,
        request.method,
        full_path,
        response.status_code,
        status_text,
        duration_ms,
    )
    return response
