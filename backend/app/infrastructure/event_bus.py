from collections import defaultdict
from collections.abc import Callable
from typing import Any, TypeVar

from app.domain.ports import IEventBus
    
E = TypeVar("E")

class EventBus(IEventBus):
    def __init__(self):
        self._handlers: dict[type, list[Callable[[Any], None]]] = defaultdict(list)
    
    #NOTE: The type of the method indicates that the handler must accept exactly the same 
    # type as the type passed in the event.
    def subscribe(self, event_type: type[E], handler: Callable[[E], None]) -> None:
        self._handlers[event_type].append(handler)
        
    def publish(self, event: object) -> None:
        for handler in self._handlers[type[event]]:
            # Call each funtion and pass the event as an argument.
            handler(event)