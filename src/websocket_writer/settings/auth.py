from pydantic_settings import BaseSettings


class AuthSettings(BaseSettings):
    url: str = None
    client_id: str = None
    client_secret: str = None
    expiry_default: int = 1800
    expiry_margin: int = 300
