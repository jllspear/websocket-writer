from .manager import DatabaseManager
from ..settings import settings

db_manager = DatabaseManager(settings.database)
