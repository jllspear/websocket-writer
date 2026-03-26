from pydantic_settings import BaseSettings


class AuthSettings(BaseSettings):
    url: str
    client_id: str
    client_secret: str
    expiry_default: int = 1800
    expiry_margin: int = 300
