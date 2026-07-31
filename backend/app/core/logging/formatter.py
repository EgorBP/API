import logging


class DetailedFormatter(logging.Formatter):
    """Log formatter that appends structured context fields to each line.

    Reads well-known optional attributes (`source`, `user_id`,
    `tg_user_id`, `gif_id`) off the `LogRecord` — typically set via the
    `extra` argument to the logging calls — and renders them as a
    ``key=value`` list consumed by the `%(extra_fields)s` placeholder in
    the format string. Fields that are absent or None are omitted.
    
    Example:
        >>> logger.info("Get user info", extra={"user_id": 42, "source": "cache"})
        2026-07-25 12:00:00 | INFO | app.services.user | user.py:get_user_info | source=cache | user_id=42 | Get user info
    """

    def format(self, record):
        """Formats a log record, injecting `record.extra_fields`.

        Args:
            record: The log record being formatted.

        Returns:
            The formatted log line.
        """
        fields = []

        if hasattr(record, "source"):
            fields.append(f"source={record.source}")

        if hasattr(record, "user_id") and record.user_id is not None:
            fields.append(f"user_id={record.user_id}")

        if hasattr(record, "tg_user_id") and record.tg_user_id is not None:
            fields.append(f"tg_user_id={record.tg_user_id}")
            
        if hasattr(record, "gif_id") and record.gif_id is not None:
            fields.append(f"gif_id={record.gif_id}")

        record.extra_fields = f" | {' | '.join(fields)}" if fields else ""

        return super().format(record)
