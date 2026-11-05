"""login events

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-31 22:10:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, Sequence[str], None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CREATE_NO_UPDATE = """
CREATE TRIGGER trg_login_events_no_update
BEFORE UPDATE ON login_events
BEGIN
    SELECT RAISE(ABORT, 'login_events is append-only');
END
"""

_CREATE_NO_DELETE = """
CREATE TRIGGER trg_login_events_no_delete
BEFORE DELETE ON login_events
BEGIN
    SELECT RAISE(ABORT, 'login_events is append-only');
END
"""


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "login_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username_attempted", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.String(length=32), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_login_events_user_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_login_events_created_at", "login_events", ["created_at"])
    op.create_index(
        "ix_login_events_username_attempted", "login_events", ["username_attempted"]
    )
    op.execute(_CREATE_NO_UPDATE)
    op.execute(_CREATE_NO_DELETE)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TRIGGER IF EXISTS trg_login_events_no_delete")
    op.execute("DROP TRIGGER IF EXISTS trg_login_events_no_update")
    op.drop_index("ix_login_events_username_attempted", table_name="login_events")
    op.drop_index("ix_login_events_created_at", table_name="login_events")
    op.drop_table("login_events")
