from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Any

T = TypeVar("T")


class WebSocketParser(Generic[T], ABC):
    @abstractmethod
    def parse(self, payload: Any) -> T:
        pass
