from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import TypeVar


class IEventBus(ABC):
    @abstractmethod
    def suscribe(self, event_type: type, handler: Callable[[TypeVar], None]) -> None: ...
    
    @abstractmethod
    def publish(self, event: object) -> None: ...
    
class IEventHandler(ABC):
    @abstractmethod
    def handle(eslf, event: object) -> None: ...