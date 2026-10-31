import logging
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.ports import IOutboxRepository
from app.infrastructure.persistence.models import OutboxEvent

logger = logging.getLogger(__name__)


class OutboxRepository(IOutboxRepository):
    """Persists notification work in its own short database transaction."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def enqueue(
        self,
        *,
        event_key: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> bool:
        async with self._session_factory() as session:
            session.add(
                OutboxEvent(
                    event_key=event_key,
                    event_type=event_type,
                    payload=payload,
                    status="pending",
                    attempts=0,
                )
            )
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                # A duplicate key means the same event was already persisted.
                logger.info("Outbox event already exists: %s", event_key)
                return False
        return True
