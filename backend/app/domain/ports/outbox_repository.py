from abc import ABC, abstractmethod
from typing import Any


class IOutboxRepository(ABC):
    @abstractmethod
    async def enqueue(
        self,
        *,
        event_key: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> bool: ...
