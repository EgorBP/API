from typing import Any


class AppException(Exception):
    """Base class for all application-level errors.

    Subclasses are caught by `AppExceptionHandlers` and converted into a
    standardized JSON error response. Raise this directly only for
    generic cases; prefer a domain-specific subclass where one exists.

    Attributes:
        status_code: Default HTTP status code returned for this error.
        error_code: Default machine-readable error code returned for this
            error.
    """
    status_code: int = 400
    error_code: str = "BAD_REQUEST"

    def __init__(
        self,
        message: str = "An application error occurred.",
        status_code: int | None = None,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initializes the exception.

        Args:
            message: Human-readable error message returned to the client.
            status_code: Overrides the class-level `status_code` if given.
            error_code: Overrides the class-level `error_code` if given.
            details: Extra structured data included in the response body,
                e.g. the offending IDs.
        """
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        if error_code is not None:
            self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class NotFoundError(AppException):
    """Base class for HTTP 404 errors."""
    status_code = 404
    error_code = "NOT_FOUND"

    def __init__(
        self,
        message: str = "Resource not found.",
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initializes the exception.

        Args:
            message: Human-readable error message returned to the client.
            error_code: Overrides the class-level `error_code` if given.
            details: Extra structured data included in the response body.
        """
        super().__init__(
            message=message,
            error_code=error_code or self.error_code,
            details=details,
        )


class UnauthorizedError(AppException):
    """Base class for HTTP 401 errors."""
    status_code = 401
    error_code = "UNAUTHORIZED"

    def __init__(
        self,
        message: str = "Authentication failed.",
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initializes the exception.

        Args:
            message: Human-readable error message returned to the client.
            error_code: Overrides the class-level `error_code` if given.
            details: Extra structured data included in the response body.
        """
        super().__init__(
            message=message,
            status_code=self.status_code,
            error_code=error_code or self.error_code,
            details=details,
        )


class UserNotFoundError(NotFoundError):
    """Raised when a user cannot be found by internal ID or Telegram ID."""

    def __init__(
        self,
        user_id: int | None = None,
        tg_user_id: int | None = None,
        message: str | None = None,
    ) -> None:
        """Initializes the exception.

        At least one of `user_id` / `tg_user_id` should be provided so the
        auto-generated message and `details` are meaningful; if neither is
        given, a generic "not found" message is used.

        Args:
            user_id: Internal ID of the user that was not found.
            tg_user_id: Telegram ID of the user that was not found.
            message: Overrides the auto-generated message if given.
        """
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
    """Raised when one or more GIFs cannot be found."""

    def __init__(
        self,
        gif_id: int | None = None,
        gif_ids: list[int] | None = None,
        user_id: int | None = None,
        tg_user_id: int | None = None,
        source: str | None = None,
        message: str | None = None,
    ) -> None:
        """Initializes the exception.

        Covers several cases: a single missing GIF (`gif_id`), a batch
        where some IDs are missing (`gif_ids`), or a user's library simply
        having no matching GIFs. `user_id` / `tg_user_id` / `source` are
        added to `details` and to the message when provided, to make the
        response more specific.

        Args:
            gif_id: ID of the single GIF that was not found.
            gif_ids: IDs of the GIFs that were not found, for batch
                lookups.
            user_id: Internal ID of the user the lookup was scoped to.
            tg_user_id: Telegram ID of the user the lookup was scoped to.
            source: Free-form label identifying which operation raised
                this error, included in `details` for easier debugging.
            message: Overrides the auto-generated message if given.
        """
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
    """Raised when one or more tags cannot be found."""

    def __init__(
        self,
        tag_id: int | None = None,
        user_id: int | None = None,
        tg_user_id: int | None = None,
        source: str | None = None,
        message: str | None = None,
    ) -> None:
        """Initializes the exception.

        Args:
            tag_id: ID of the tag that was not found.
            user_id: Internal ID of the user the lookup was scoped to.
            tg_user_id: Telegram ID of the user the lookup was scoped to.
            source: Free-form label identifying which operation raised
                this error, included in `details` for easier debugging.
            message: Overrides the auto-generated message if given.
        """
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
    """Raised when authentication credentials are invalid, expired, or missing."""

    def __init__(
            self, 
            message: str = "Invalid credentials."
    ) -> None:
        """Initializes the exception.

        Args:
            message: Human-readable error message returned to the client.
        """
        super().__init__(
            message=message,
            error_code="INVALID_CREDENTIALS",
        )
