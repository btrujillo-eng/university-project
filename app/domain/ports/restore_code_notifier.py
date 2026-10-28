from abc import ABC, abstractmethod


class IRestoreCodeNotifier(ABC):
    @abstractmethod
    async def send_restore_code(self, email: str, code: str) -> None: ...
