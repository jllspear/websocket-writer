import asyncio
import logging
from collections import defaultdict
from types import ModuleType

from sqlmodel import SQLModel

from .database.writer import BatchWriter

from .settings import settings

from .websocket.message_buffer import ParsedObjectBuffer
from .websocket.parser import WebSocketParser
from .websocket.reader import WebSocketReader
from .websocket.websocket_manager import WebSocketClient

logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s|%(levelname)s|%(name)s|%(message)s'
)

logger = logging.getLogger(__name__)
logger.setLevel(settings.log_level)

class WebSocketWriter:

    def __init__(self,
                 parser_module: ModuleType,
                 commit_interval = 3,
                 worker_stack_size = 5) -> None:
        self.parser_module = parser_module
        self.commit_interval = commit_interval
        self.worker_stack_size = worker_stack_size

    def get_parser_from_config(self) -> dict[str, WebSocketParser]:
        parsers = defaultdict(WebSocketParser)
        for topic, parser_class_name in settings.broker.topics.items():
            parser_cls = getattr(self.parser_module, parser_class_name)
            logger.info(f"Custom {parser_cls} found for topic {topic}")

            parsers[topic] = parser_cls()
        return parsers

    def run(self):

        parsers = self.get_parser_from_config()

        buffer = ParsedObjectBuffer[SQLModel]()

        writer = BatchWriter(buffer, self.commit_interval)
        writer.start()

        reader = WebSocketReader(buffer, parsers)

        logger.info('Starting loop...')
        asyncio.run(WebSocketClient(reader.on_message, self.worker_stack_size).run())



