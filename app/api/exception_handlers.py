import logging
from typing import Any
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from app.core.exceptions import TgUserNotFoundError, UserGifsNotFoundError, GifNotFoundError, UserTagsNotFoundError, \
    InvalidCredentialsError


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
        to_register = {
            ValueError: self._handle_value_error,
            RequestValidationError: self._handle_validation_error,
            IntegrityError: self._handle_integrity_error,
            OperationalError: self._handle_operational_error,
            SQLAlchemyError: self._handle_sqlalchemy_error,
            TgUserNotFoundError: self._handle_tg_user_not_found_error,
            UserGifsNotFoundError: self._handle_gifs_not_found_error,
            GifNotFoundError: self._handle_gif_not_found_error,
            UserTagsNotFoundError: self._handle_user_tags_not_found_error,
            InvalidCredentialsError: self._handle_invalid_credentials_error
        }
        
        for error, handler in to_register.items():
            app.add_exception_handler(error, handler)

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
        exc: RequestValidationError
    ) -> JSONResponse:
        errors = exc.errors()

        self.logger.warning(
            "Request validation failed on %s %s: %s",
            request.method,
            request.url,
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
        exc: IntegrityError
    ) -> JSONResponse:
        detail, status_code = self._map_integrity_error(exc)

        self.logger.info(
            "Database integrity error on %s %s: %s",
            request.method,
            request.url,
            detail,
        )

        return JSONResponse(
            status_code=status_code,
            content={"detail": detail},
        )

    async def _handle_operational_error(
        self,
        request: Request,
        exc: OperationalError
    ) -> JSONResponse:
        self.logger.exception(
            "Database operational error on %s %s",
            request.method,
            request.url,
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "Service temporarily unavailable."},
        )

    async def _handle_sqlalchemy_error(
        self,
        request: Request,
        exc: SQLAlchemyError
    ) -> JSONResponse:
        self.logger.exception(
            "SQLAlchemy error on %s %s",
            request.method,
            request.url,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal database error."},
        )
    
    async def _handle_tg_user_not_found_error(
            self,
            request: Request,
            exc: TgUserNotFoundError
    ) -> JSONResponse:
        self.logger.warning(
            "User not found on %s %s",
            request.method,
            request.url,
            extra={
                "tg_user_id": exc.tg_user_id
            }
        )

        return JSONResponse(
            status_code=404,
            content={"detail": str(exc)},
        )
    
    async def _handle_gifs_not_found_error(
            self,
            request: Request,
            exc: UserGifsNotFoundError
    ) -> JSONResponse:
        self.logger.info(
            "User GIF's not found on %s %s",
            request.method,
            request.url,
            extra={
                "source": exc.source,
                "user_id": exc.user_id,
                "tg_user_id": exc.tg_user_id,
            }
        )

        return JSONResponse(
            status_code=404,
            content={"detail": str(exc)},
        )
    
    async def _handle_gif_not_found_error(
            self,
            request: Request,
            exc: GifNotFoundError
    ):
        self.logger.warning(
            "Gif not found on %s %s",
            request.method,
            request.url,
            extra={
                "gif_id": exc.gif_id,
                "user_id": exc.user_id
            }
        )

        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "detail": str(exc),
                "gif_id": exc.gif_id
            },
        )
    
    async def _handle_user_tags_not_found_error(
            self,
            request: Request,
            exc: UserTagsNotFoundError
    ):
        self.logger.info(
            "User tags not found %s %s",
            request.method,
            request.url,
            extra={
                "user_id": exc.user_id
            }
        )

        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "detail": str(exc),
            },
        )
    
    async def _handle_invalid_credentials_error(
            self,
            request: Request,
            exc: InvalidCredentialsError
    ):
        self.logger.warning(
            "Invalid credentials %s %s",
            request.method,
            request.url,
        )

        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "detail": str(exc),
            },
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
