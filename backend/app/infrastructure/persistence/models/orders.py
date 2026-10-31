from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Identity,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.domain.enums import DeliveryStatus, PaymentMethods, PaymentStatus
from app.infrastructure.persistence.models.base import Base
from app.infrastructure.persistence.models.enum_utils import get_enum_value

if TYPE_CHECKING:
    from app.infrastructure.persistence.models.order_items import OrderItem
    from app.infrastructure.persistence.models.users import User


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (UniqueConstraint("user_id", "idempotency_key", name="uq_orders_user_idempotency_key"),)

    id: Mapped[int] = mapped_column(Integer, Identity(always=True), primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    courier_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    customer_name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    total_price: Mapped[Decimal] = mapped_column(Numeric(precision=10, scale=2), nullable=False)
    delivery_status: Mapped[DeliveryStatus] = mapped_column(
        Enum(DeliveryStatus, name="delivery_status", values_callable=get_enum_value), nullable=False
    )
    payment_method: Mapped[PaymentMethods] = mapped_column(
        Enum(PaymentMethods, name="payment_method", values_callable=get_enum_value), nullable=False
    )
    payment_status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status", values_callable=get_enum_value), nullable=False
    )
    shipping_street: Mapped[str] = mapped_column(String(80), nullable=False)
    shipping_neighborhood: Mapped[str] = mapped_column(String(60), nullable=False, default="")
    shipping_department: Mapped[str] = mapped_column(String(60), nullable=False, default="")
    shipping_details: Mapped[str] = mapped_column(String(120), nullable=False)
    shipping_instructions: Mapped[str | None] = mapped_column(String(250), nullable=True)
    shipping_city: Mapped[str] = mapped_column(String(60), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), onupdate=func.now()
    )
    phone_number: Mapped[str] = mapped_column(String(10), nullable=False)

    user: Mapped[User] = relationship(back_populates="orders", foreign_keys=[user_id])
    order_items: Mapped[list[OrderItem]] = relationship(back_populates="order")
