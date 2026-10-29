"""Support passwordless Google-authenticated users.

Revision ID: 20261029_03
Revises: 20261029_02
Create Date: 2026-10-29
"""
from alembic import op

revision = "20261029_03"
down_revision = "20261029_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # IF NOT EXISTS keeps this safe when the columns/index were applied manually.
    op.execute("ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS google_sub VARCHAR(255)")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_users_google_sub "
        "ON users (google_sub)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_users_google_sub")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS google_sub")
    # This requires all rows to have a password hash; Google-only accounts must
    # be handled before downgrading.
    op.execute("ALTER TABLE users ALTER COLUMN password_hash SET NOT NULL")
