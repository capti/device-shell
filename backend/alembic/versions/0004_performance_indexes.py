"""performance indexes

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-20 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: Union[str, Sequence[str], None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add indexes for date-range filters and ordering."""
    op.create_index("ix_device_events_created_at", "device_events", ["created_at"])
    op.create_index(
        "ix_checkouts_taken_at_id", "checkouts", ["taken_at", "id"]
    )
    op.create_index("ix_checkouts_returned_at", "checkouts", ["returned_at"])


def downgrade() -> None:
    """Drop only the three indexes added by this revision."""
    op.drop_index("ix_checkouts_returned_at", table_name="checkouts")
    op.drop_index("ix_checkouts_taken_at_id", table_name="checkouts")
    op.drop_index("ix_device_events_created_at", table_name="device_events")
