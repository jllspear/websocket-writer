from pydantic_settings import BaseSettings


class WebSocketSettings(BaseSettings):
    url: str
