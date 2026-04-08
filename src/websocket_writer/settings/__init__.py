from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

from .websocket import WebSocketSettings
from .database import DatabaseSettings
from .stomp import StompSettings
from .auth import AuthSettings


class Settings(BaseSettings):
    database: DatabaseSettings = None
    websocket: WebSocketSettings = None
    stomp: StompSettings = None
    auth: Optional[AuthSettings] = None

    log_level: str = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="allow",
    )


settings = Settings()
