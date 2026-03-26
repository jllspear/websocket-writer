from pydantic_settings import BaseSettings


class WebSocketSettings(BaseSettings):
    url: str
    parser_dict: dict[str, str]