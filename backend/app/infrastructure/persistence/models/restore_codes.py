from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Identity, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.persistence.models.base import Base

if TYPE_CHECKING:
    from app.infrastructure.persistence.models.users import User

class RestoreCode(Base):
    __tablename__ = 'restore_codes'
    __table_args__ = (
        Index(
            "uq_restore_codes_one_active_per_user",
            "user_id",
            unique=True,
            postgresql_where=text("is_active = true"),
        ),
    )
    
    id: Mapped[int] = mapped_column(Integer, Identity(always=True), primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'))
    code_hash: Mapped[str] = mapped_column(String(255))
    was_used: Mapped[bool] = mapped_column(Boolean, server_default=text('false'))
    expired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text('true'))
    
    user: Mapped[User] = relationship(back_populates='restore_codes')