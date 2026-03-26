import geoalchemy2
import sqlalchemy
from sqlalchemy import URL
from sqlalchemy.orm import Session as SessionSQLAlchemy
from sqlmodel import create_engine, Session, SQLModel

from ..settings.database import DatabaseSettings


class DatabaseManager:
    def __init__(self, settings: DatabaseSettings):
        if not settings:
            raise ValueError("Database settings must be provided.")

        self.settings: DatabaseSettings = settings
        self.versions = {
            "sqlalchemy": sqlalchemy.__version__,
            "geoalchemy2": geoalchemy2.__version__,
        }

        self.port = settings.port

        if not self.validate_config():
            raise ValueError(
                "Unimplemented DB provider or dialect. Supported providers are: 'postgresql' ('psycopg')"
            )

        self.engine = create_engine(
            self.connection_url,
            echo=settings.echo,
            pool_size=50,
            max_overflow=100,
            pool_timeout=15,
        )

    def validate_config(self):
        return (
            self.settings.provider == "postgresql"
            and self.settings.dialect == "psycopg"
        )

    @property
    def connection_url(self):
        return URL.create(
            f"{self.settings.provider}+{self.settings.dialect}",
            username=self.settings.user,
            password=self.settings.password,
            host=self.settings.host,
            port=self.port,
            database=self.settings.database,
            query={"application_name": self.settings.client_name},
        )

    def create_db(self):
        SQLModel.metadata.create_all(self.engine)

    def get_session(self):
        with Session(self.engine) as session:
            yield session

    def get_static_session(self):
        with Session(self.engine) as session:
            return session

    def get_sqlalchemy_session(self, **kwargs):
        return SessionSQLAlchemy(self.engine, **kwargs)
