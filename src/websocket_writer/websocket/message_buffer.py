from collections import deque
from typing import TypeVar, Generic
from threading import Lock

T = TypeVar("T")


class ParsedObjectBuffer(Generic[T]):
    def __init__(self):
        self._buffer = deque()
        self._lock = Lock()

    def add(self, element: T):
        self._buffer.append(element)

    def get_and_clear(self) -> list[T]:
        with self._lock:
            old = self._buffer
            self._buffer = deque()

        return list(old)
