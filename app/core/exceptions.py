from typing import Any


class AppException(Exception):
    """Base exception for all application-level errors."""

    status_code: int = 400
    error_code: str = "BAD_REQUEST"

    def __init__(
        self,
        message: str = "An application error occurred.",
        status_code: int | None = None,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        if error_code is not None:
            self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class NotFoundError(AppException):
    """Base exception for HTTP 404 Not Found errors."""

    status_code = 404
    error_code = "NOT_FOUND"

    def __init__(
        self,
        message: str = "Resource not found.",
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=404,
            error_code=error_code or self.error_code,
            details=details,
        )


class UnauthorizedError(AppException):
    """Base exception for HTTP 401 Unauthorized errors."""

    status_code = 401
    error_code = "UNAUTHORIZED"

    def __init__(
        self,
        message: str = "Authentication failed.",
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=401,
            error_code=error_code or self.error_code,
            details=details,
        )


# =====================================================================
# Domain Exceptions
# =====================================================================


class UserNotFoundError(NotFoundError):
    """Raised when a system user or Telegram user is not found."""

    def __init__(
        self,
        user_id: int | None = None,
        tg_user_id: int | None = None,
        message: str | None = None,
    ) -> None:
        details: dict[str, Any] = {}
        if user_id is not None:
            details["user_id"] = user_id
        if tg_user_id is not None:
            details["tg_user_id"] = tg_user_id

        if message is None:
            if user_id is not None:
                message = f"User with ID {user_id} not found."
            elif tg_user_id is not None:
                message = f"Telegram user with ID {tg_user_id} not found."
            else:
                message = "User not found."

        super().__init__(
            message=message,
            error_code="USER_NOT_FOUND",
            details=details,
        )


class GifNotFoundError(NotFoundError):
    """Raised when one or multiple GIFs (or a user's GIFs) are not found."""

    def __init__(
        self,
        gif_id: int | None = None,
        gif_ids: list[int] | None = None,
        user_id: int | None = None,
        tg_user_id: int | None = None,
        source: str | None = None,
        message: str | None = None,
    ) -> None:
        details: dict[str, Any] = {}
        if gif_id is not None:
            details["gif_id"] = gif_id
        if gif_ids:
            details["gif_ids"] = gif_ids
        if user_id is not None:
            details["user_id"] = user_id
        if tg_user_id is not None:
            details["tg_user_id"] = tg_user_id
        if source:
            details["source"] = source

        if message is None:
            if gif_ids:
                message = f"GIFs with IDs {gif_ids} not found"
            elif gif_id is not None:
                message = f"GIF with ID {gif_id} not found"
            else:
                message = "GIFs not found"

            if user_id is not None:
                message += f" for user {user_id}."
            elif tg_user_id is not None:
                message += f" for Telegram user {tg_user_id}."
            else:
                message += "."

        super().__init__(
            message=message,
            error_code="GIF_NOT_FOUND",
            details=details,
        )


class TagNotFoundError(NotFoundError):
    """Raised when one or multiple tags are not found."""

    def __init__(
        self,
        tag_id: int | None = None,
        user_id: int | None = None,
        tg_user_id: int | None = None,
        source: str | None = None,
        message: str | None = None,
    ) -> None:
        details: dict[str, Any] = {}
        if tag_id is not None:
            details["tag_id"] = tag_id
        if user_id is not None:
            details["user_id"] = user_id
        if tg_user_id is not None:
            details["tg_user_id"] = tg_user_id
        if source:
            details["source"] = source

        if message is None:
            if tag_id is not None:
                message = f"Tag with ID {tag_id} not found"
            else:
                message = "Tags not found"

            if user_id is not None:
                message += f" for user {user_id}."
            elif tg_user_id is not None:
                message += f" for Telegram user {tg_user_id}."
            else:
                message += "."

        super().__init__(
            message=message,
            error_code="TAG_NOT_FOUND",
            details=details,
        )


class InvalidCredentialsError(UnauthorizedError):
    """Raised when authentication credentials are invalid or missing."""

    def __init__(self, message: str = "Invalid credentials.") -> None:
        super().__init__(
            message=message,
            error_code="INVALID_CREDENTIALS",
        )
