from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

APP_DIR = Path(__file__).resolve().parent
APP_NAME = APP_DIR.name

TEMPLATES_DIR = APP_DIR / "templates"
STATIC_DIR = APP_DIR / "static"
CSS_DIR = STATIC_DIR / "css"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    ENABLE_LITESTAR_DEBUG_MODE: bool = False
    ENABLE_HTML_RESPONSE_COMPRESSION: bool = True
    ENABLE_CORS: bool = True
    ENABLE_CSRF: bool = True
    ENABLE_TEMPLATE_RESPONSES: bool = False
    ENABLE_OPENAPI_SCHEMA: bool = False
    OPENAPI_SCHEMA_PATH: str = "/docs"


SETTINGS = Settings()
