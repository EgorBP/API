import logging.config


LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,

    "formatters": {
        "default": {
            "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        },
        "detailed": {
            "()": "app.core.logging.formatter.DetailedFormatter",
            "format": "%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(funcName)s%(extra_fields)s | %(message)s",
        },
    },

    "handlers": {
        "default": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": "ext://sys.stdout",
        },
        "detailed_console": {
            "class": "logging.StreamHandler",
            "formatter": "detailed",
            "stream": "ext://sys.stdout",
        },
    },

    "root": {
        "level": "INFO",
        "handlers": ["default"],
    },

    "loggers": {
        "app": {
            "level": "DEBUG",
            "handlers": ["detailed_console"],
            "propagate": False,
        },
        "app.lifespan": {
            "level": "INFO",
            "handlers": ["default"],
            "propagate": False,
        },
        "app.api.exceptions": {
            "level": "INFO",
            "handlers": ["default"],
            "propagate": False,
        },
        "app.access": {
            "level": "INFO",
            "handlers": ["default"],
            "propagate": False,
        },

        "uvicorn": {
            "level": "INFO",
            "handlers": ["default"],
            "propagate": False,
        },
        "uvicorn.error": {
            "level": "INFO",
            "handlers": ["default"],
            "propagate": False,
        },
        "uvicorn.access": {
            "level": "WARNING",
            "handlers": ["default"],
            "propagate": False,
        },
        "alembic": {
            "level": "INFO",
            "handlers": ["default"],
            "propagate": False,
        },
    },
}


def setup_logging() -> None:
    logging.config.dictConfig(LOGGING_CONFIG)
