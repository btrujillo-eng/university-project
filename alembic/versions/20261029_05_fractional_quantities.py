"""Support fractional stock and item quantities.

Revision ID: 20261029_05
Revises: 20261029_04
Create Date: 2026-10-29
"""
from alembic import op
import sqlalchemy as sa

revision = "20261029_05"
down_revision = "20261029_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "products",
        "stock",
        existing_type=sa.Integer(),
        type_=sa.Numeric(10, 3),
        existing_nullable=False,
        postgresql_using="stock::numeric(10,3)",
    )
    op.alter_column(
        "cart_items",
        "quantity",
        existing_type=sa.Integer(),
        type_=sa.Numeric(10, 3),
        existing_nullable=False,
        postgresql_using="quantity::numeric(10,3)",
    )
    op.alter_column(
        "order_items",
        "quantity",
        existing_type=sa.Integer(),
        type_=sa.Numeric(10, 3),
        existing_nullable=False,
        postgresql_using="quantity::numeric(10,3)",
    )


def downgrade() -> None:
    # Downgrade rounds fractional values to the nearest integer.
    op.alter_column(
        "order_items",
        "quantity",
        existing_type=sa.Numeric(10, 3),
        type_=sa.Integer(),
        existing_nullable=False,
        postgresql_using="round(quantity)::integer",
    )
    op.alter_column(
        "cart_items",
        "quantity",
        existing_type=sa.Numeric(10, 3),
        type_=sa.Integer(),
        existing_nullable=False,
        postgresql_using="round(quantity)::integer",
    )
    op.alter_column(
        "products",
        "stock",
        existing_type=sa.Numeric(10, 3),
        type_=sa.Integer(),
        existing_nullable=False,
        postgresql_using="round(stock)::integer",
    )
