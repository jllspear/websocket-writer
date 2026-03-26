import json
import logging

from pydantic import ValidationError

from .message_buffer import ParsedObjectBuffer
from .parser import WebSocketParser

logger = logging.getLogger(__name__)


class WebSocketReader:
    def __init__(self, buffer: ParsedObjectBuffer, parsers: dict[str, WebSocketParser]):
        self.parsers = parsers
        self.buffer = buffer

    def on_message(self, msg, topic):
        try:
            logger.debug("Received message on topic {}".format(topic))
            payload = json.loads(msg.payload.decode("utf-8"))

            logger.debug("Received payload {}".format(payload))
            parser = self.parsers[topic.split("/")[-1]]
            parsed_element = parser.parse(payload)

            if parsed_element:
                self.buffer.add(parsed_element)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON message: {e}")
            return

        except ValidationError as e:
            logger.error(f"Error processing message: {e}")
            return
