import logging
import time
from threading import Thread

from . import db_manager
from ..websocket.message_buffer import ParsedObjectBuffer

logger = logging.getLogger(__name__)

class BatchWriter:
    def __init__(self, buffer: ParsedObjectBuffer, commit_interval: int):
        self.buffer = buffer
        self._running = False
        self.thread = None
        if commit_interval < 1:
            logger.warning(f"Warning: commit_interval {commit_interval}s is below minimum. Using 1s instead.")
            self.commit_interval = 1
        else:
            self.commit_interval = commit_interval

    def _write_loop(self):
        while self._running:
            next_commit_time = time.time() + self.commit_interval

            self.commit_buffered_elements()

            remaining_time = next_commit_time - time.time()
            if remaining_time > 0:
                time.sleep(remaining_time)

    def commit_buffered_elements(self):
        elements = self.buffer.get_and_clear()
        if not elements:
            logger.info("No elements to commit")
            return

        session = db_manager.get_sqlalchemy_session()

        try:
            with session.begin():
                start_time = time.time()
                session.add_all(elements)

            logger.info(f"Successfully committed {len(elements)} elements in {time.time() - start_time} seconds")

        except Exception as e:
            logger.error(f"Database error: {e}")
        finally:
            session.close()

    def start(self):
        self._running = True
        self.thread = Thread(target=self._write_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self._running = False
        if self.thread:
            self.thread.join()
        self.commit_buffered_elements()
