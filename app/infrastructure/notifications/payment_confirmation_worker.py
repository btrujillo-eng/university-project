import asyncio
import html
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import resend
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.config import Settings
from app.infrastructure.persistence.models import OutboxEvent

logger = logging.getLogger(__name__)


class PaymentConfirmationOutboxWorker:
    """Polls PostgreSQL for durable card-payment confirmation emails."""

    EVENT_TYPE = "payment.card.succeeded"
    MAX_ATTEMPTS = 8
    POLL_SECONDS = 2
    LOCK_SECONDS = 120

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        settings: Settings,
    ) -> None:
        self._session_factory = session_factory
        self._settings = settings

    async def run(self) -> None:
        while True:
            event_id = await self._claim_one()
            if event_id is None:
                await asyncio.sleep(self.POLL_SECONDS)
                continue
            await self._deliver(event_id)

    async def _claim_one(self) -> int | None:
        now = datetime.now(UTC)
        async with self._session_factory() as session:
            async with session.begin():
                statement = (
                    select(OutboxEvent)
                    .where(
                        OutboxEvent.event_type == self.EVENT_TYPE,
                        OutboxEvent.attempts < self.MAX_ATTEMPTS,
                        or_(
                            (OutboxEvent.status == "pending") & (OutboxEvent.available_at <= now),
                            (OutboxEvent.status == "processing") & (OutboxEvent.locked_until < now),
                        ),
                    )
                    .order_by(OutboxEvent.created_at)
                    .with_for_update(skip_locked=True)
                    .limit(1)
                )
                event = (await session.execute(statement)).scalar_one_or_none()
                if event is None:
                    return None
                event.status = "processing"
                event.attempts += 1
                event.locked_until = now + timedelta(seconds=self.LOCK_SECONDS)
                return event.id

    async def _deliver(self, event_id: int) -> None:
        async with self._session_factory() as session:
            event = await session.get(OutboxEvent, event_id)
            if event is None:
                return
            payload = dict(event.payload)

        try:
            await asyncio.to_thread(self._send_email, payload)
        except Exception as exc:
            logger.exception("Payment confirmation email failed for outbox event %s", event_id)
            await self._schedule_retry(event_id, str(exc))
            return

        async with self._session_factory() as session:
            event = await session.get(OutboxEvent, event_id)
            if event is None:
                return
            event.status = "sent"
            event.processed_at = datetime.now(UTC)
            event.locked_until = None
            event.last_error = None
            await session.commit()
        logger.info("Payment confirmation email sent for outbox event %s", event_id)

    def _send_email(self, payload: dict[str, Any]) -> None:
        resend.api_key = self._settings.resend_api_key.get_secret_value()
        name = html.escape(str(payload["first_name"]))
        transaction_id = html.escape(str(payload["transaction_id"]))
        amount = html.escape(str(payload["amount"]))
        currency = html.escape(str(payload["currency"]).upper())
        created_at = html.escape(str(payload["created_at"]))
        network = html.escape(str(payload["processing_network"]))
        last_digits = html.escape(str(payload["last_digits"]))
        body = f"""
        <html><body>
          <h2>Pago confirmado</h2>
          <p>Hola <strong>{name}</strong>, tu pago con tarjeta fue aprobado.</p>
          <p><strong>Transacción:</strong> {transaction_id}</p>
          <p><strong>Total:</strong> {amount} {currency}</p>
          <p><strong>Fecha:</strong> {created_at}</p>
          <p><strong>Tarjeta:</strong> {network} terminada en {last_digits}</p>
          <p>Gracias por tu compra.</p>
        </body></html>
        """
        resend.Emails.send(
            {
                "from": self._settings.resend_from_email,
                "to": [str(payload["email"])],
                "subject": f"Confirmación de pago {transaction_id}",
                "html": body,
            }
        )

    async def _schedule_retry(self, event_id: int, error: str) -> None:
        async with self._session_factory() as session:
            event = await session.get(OutboxEvent, event_id)
            if event is None:
                return
            event.locked_until = None
            event.last_error = error[:1000]
            if event.attempts >= self.MAX_ATTEMPTS:
                event.status = "failed"
                logger.error("Outbox event %s exhausted all retries", event_id)
            else:
                event.status = "pending"
                delay_seconds = min(30 * (2 ** (event.attempts - 1)), 3600)
                event.available_at = datetime.now(UTC) + timedelta(seconds=delay_seconds)
            await session.commit()
