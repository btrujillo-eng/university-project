"""Persist idempotency keys for checkout orders.

Revision ID: 20261029_04
Revises: 20261029_03
Create Date: 2026-10-29
"""
from alembic import op
import sqlalchemy as sa

revision = "20261029_04"
down_revision = "20261029_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("idempotency_key", sa.String(length=255), nullable=True))
    op.create_unique_constraint(
        "uq_orders_user_idempotency_key",
        "orders",
        ["user_id", "idempotency_key"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_orders_user_idempotency_key", "orders", type_="unique")
    op.drop_column("orders", "idempotency_key")
