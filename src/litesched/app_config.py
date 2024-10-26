from importlib import metadata
from pathlib import Path

from litestar.config.compression import CompressionConfig
from litestar.config.cors import CORSConfig
from litestar.config.csrf import CSRFConfig
from litestar.contrib.jinja import JinjaTemplateEngine
from litestar.logging import LoggingConfig
from litestar.openapi.config import OpenAPIConfig
from litestar.template.config import TemplateConfig

from litesched.config import APP_NAME, SETTINGS, TEMPLATES_DIR


def get_compression_config(
    *,
    is_enabled: bool = SETTINGS.ENABLE_HTML_RESPONSE_COMPRESSION,
) -> CompressionConfig | None:
    if not is_enabled:
        return None
    return CompressionConfig(backend="gzip")


def get_cors_config(
    *,
    is_enabled: bool = SETTINGS.ENABLE_CORS,
) -> CORSConfig | None:
    if not is_enabled:
        return None
    return CORSConfig()


def get_csrf_config(
    *,
    is_enabled: bool = SETTINGS.ENABLE_CSRF,
    secret_key: str = SETTINGS.SECRET_KEY,
) -> CSRFConfig | None:
    if not is_enabled:
        return None
    return CSRFConfig(secret=secret_key)


def get_debug_config(
    *,
    is_enabled: bool = SETTINGS.ENABLE_LITESTAR_DEBUG_MODE,
) -> bool:
    return is_enabled


def get_openapi_config(
    *,
    is_enabled: bool = SETTINGS.ENABLE_OPENAPI_SCHEMA,
    title: str = APP_NAME,
    version: str = metadata.version(APP_NAME),
    path: str = SETTINGS.OPENAPI_SCHEMA_PATH,
) -> OpenAPIConfig | None:
    if not is_enabled:
        return None
    return OpenAPIConfig(title=title, version=version, path=path)


def get_template_config(
    *,
    is_enabled: bool = SETTINGS.ENABLE_TEMPLATE_RESPONSES,
    directory: Path = TEMPLATES_DIR,
) -> TemplateConfig | None:
    if not is_enabled:
        return None
    return TemplateConfig(directory=directory, engine=JinjaTemplateEngine)


def get_logging_config() -> LoggingConfig:
    return LoggingConfig(
        configure_root_logger=False,
        log_exceptions="always",
        formatters={
            "standard": {
                "format": r"%(asctime)s %(levelname)-8s %(message)s",
                "datefmt": r"%Y-%m-%dT%H:%M:%S%z",
            },
        },
        handlers={
            "app_log_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "standard",
                "level": "DEBUG",
                "filename": f".logs/{APP_NAME}.log",
                "maxBytes": 1024 * 1024,
                "backupCount": 3,
            },
            "app_log_queue_handler": {
                "class": "logging.handlers.QueueHandler",
                "level": "DEBUG",
                "queue": {
                    "()": "queue.Queue",
                    "maxsize": -1,
                },
                "listener": "litestar.logging.standard.LoggingQueueListener",
                "handlers": ["app_log_file"],
            },
            "apscheduler_log_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "standard",
                "level": "INFO",
                "filename": ".logs/apscheduler.log",
                "maxBytes": 1024 * 1024,
                "backupCount": 3,
            },
            "apscheduler_log_queue_handler": {
                "class": "logging.handlers.QueueHandler",
                "level": "INFO",
                "queue": {
                    "()": "queue.Queue",
                    "maxsize": -1,
                },
                "listener": "litestar.logging.standard.LoggingQueueListener",
                "handlers": ["apscheduler_log_file"],
            },
        },
        loggers={
            APP_NAME: {
                "level": "DEBUG",
                "handlers": ["app_log_queue_handler"],
                "propagate": False,
            },
            "apscheduler": {
                "level": "DEBUG",
                "handlers": ["apscheduler_log_queue_handler"],
                "propagate": False,
            },
        },
    )
