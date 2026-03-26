from pydantic_settings import BaseSettings


class StompSettings(BaseSettings):
    remote_host: str
    main_topic: str
    sub_topic: str
