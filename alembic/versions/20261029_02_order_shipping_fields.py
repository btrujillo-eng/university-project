"""Add shipping fields and customer name to orders.

Revision ID: 20261029_02
Revises: 20261028_01
Create Date: 2026-10-29
"""
from alembic import op
import sqlalchemy as sa

revision = "20261029_02"
down_revision = "20261028_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("customer_name", sa.String(100), nullable=False, server_default=""))
    op.add_column("orders", sa.Column("shipping_neighborhood", sa.String(60), nullable=False, server_default=""))
    op.add_column("orders", sa.Column("shipping_department", sa.String(60), nullable=False, server_default=""))
    op.add_column("orders", sa.Column("shipping_instructions", sa.String(250), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "shipping_instructions")
    op.drop_column("orders", "shipping_department")
    op.drop_column("orders", "shipping_neighborhood")
    op.drop_column("orders", "customer_name")
