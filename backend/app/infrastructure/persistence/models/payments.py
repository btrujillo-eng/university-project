from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, Identity, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.domain.enums import PaymentMethods, PaymentStatus
from app.infrastructure.persistence.models.base import Base
from app.infrastructure.persistence.models.enum_utils import get_enum_value

if TYPE_CHECKING:
    from app.infrastructure.persistence.models.orders import Order


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, Identity(always=True), primary_key=True)
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status", values_callable=get_enum_value), nullable=False
    )
    method: Mapped[PaymentMethods] = mapped_column(
        # Keep this name aligned with the existing PostgreSQL enum type.
        Enum(PaymentMethods, name="payment_methods", values_callable=get_enum_value), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), onupdate=func.now()
    )

    order: Mapped[Order | None] = relationship(
        back_populates="payment",
        foreign_keys="Order.payment_id",
        uselist=False,
    )
