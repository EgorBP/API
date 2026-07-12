import logging
from typing import Any
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError


class AppExceptionHandlers:
    """
    Registers FastAPI exception handlers for application-level errors.

    Converts internal exceptions into HTTP responses and logs
    unexpected failures with traceback information.
    """
    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger or logging.getLogger("app.api.exceptions")

    def register(self, app: FastAPI) -> None:
        """
        Attach exception handlers to FastAPI application instance.

        :param app: FastAPI application where handlers will be registered.
        """
        app.add_exception_handler(ValueError, self._handle_value_error)
        app.add_exception_handler(RequestValidationError, self._handle_validation_error)
        app.add_exception_handler(IntegrityError, self._handle_integrity_error)
        app.add_exception_handler(OperationalError, self._handle_operational_error)
        app.add_exception_handler(SQLAlchemyError, self._handle_sqlalchemy_error)
        app.add_exception_handler(Exception, self._handle_unhandled_exception)

    async def _handle_value_error(self, request: Request, exc: ValueError) -> JSONResponse:
        self.logger.warning(
            "ValueError on %s %s: %s",
            request.method,
            request.url.path,
            exc,
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc)},
        )

    async def _handle_validation_error(
        self,
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        errors = exc.errors()

        self.logger.warning(
            "Request validation failed on %s %s: %s",
            request.method,
            request.url.path,
            self._compact_validation_errors(errors),
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": "Validation error.",
                "errors": errors,
            },
        )

    async def _handle_integrity_error(
        self,
        request: Request,
        exc: IntegrityError,
    ) -> JSONResponse:
        detail, status_code = self._map_integrity_error(exc)

        self.logger.info(
            "Database integrity error on %s %s: %s",
            request.method,
            request.url.path,
            detail,
        )

        return JSONResponse(
            status_code=status_code,
            content={"detail": detail},
        )

    async def _handle_operational_error(
        self,
        request: Request,
        exc: OperationalError,
    ) -> JSONResponse:
        self.logger.exception(
            "Database operational error on %s %s",
            request.method,
            request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "Service temporarily unavailable."},
        )

    async def _handle_sqlalchemy_error(
        self,
        request: Request,
        exc: SQLAlchemyError,
    ) -> JSONResponse:
        self.logger.exception(
            "SQLAlchemy error on %s %s",
            request.method,
            request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal database error."},
        )

    async def _handle_unhandled_exception(
        self,
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        self.logger.exception(
            "Unhandled exception on %s %s",
            request.method,
            request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Unexpected internal server error."},
        )

    @staticmethod
    def _compact_validation_errors(errors: list[dict[str, Any]]) -> list[str]:
        compact: list[str] = []
        for err in errors:
            loc = ".".join(str(part) for part in err.get("loc", []))
            msg = err.get("msg", "Invalid value")
            compact.append(f"{loc}: {msg}" if loc else msg)
        return compact

    @staticmethod
    def _map_integrity_error(exc: IntegrityError) -> tuple[str, int]:
        """
        Maps PostgreSQL integrity violation codes to HTTP status codes.

        Handles:
        
        - 23505: unique constraint violation
        - 23503: foreign key violation
        - 23502: not null violation
        """
        orig = getattr(exc, "orig", None)

        pgcode = getattr(orig, "pgcode", None)
        if pgcode == "23505":
            return "Resource already exists.", status.HTTP_409_CONFLICT
        if pgcode == "23503":
            return "Referenced resource does not exist.", status.HTTP_409_CONFLICT
        if pgcode == "23502":
            return "Required field is missing.", status.HTTP_400_BAD_REQUEST

        return "Data conflict.", status.HTTP_409_CONFLICT
