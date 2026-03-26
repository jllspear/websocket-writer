from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    provider: str
    dialect: str
    host: str
    port: int
    user: str
    password: str
    database: str
    client_name: str
    echo: bool
