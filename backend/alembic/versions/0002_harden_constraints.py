"""harden constraints and append-only audit

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-27 22:30:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CHECK_EXPRESSION = (
    "(returned_at IS NULL AND closed_reason IS NULL) "
    "OR (returned_at IS NOT NULL AND closed_reason IS NOT NULL)"
)

_CREATE_NO_UPDATE = """
CREATE TRIGGER trg_device_events_no_update
BEFORE UPDATE ON device_events
BEGIN
    SELECT RAISE(ABORT, 'device_events is append-only');
END
"""

_CREATE_NO_DELETE = """
CREATE TRIGGER trg_device_events_no_delete
BEFORE DELETE ON device_events
BEGIN
    SELECT RAISE(ABORT, 'device_events is append-only');
END
"""


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("checkouts", recreate="always") as batch_op:
        batch_op.create_check_constraint(
            "ck_checkouts_returned_closed_reason", _CHECK_EXPRESSION
        )
    op.execute(_CREATE_NO_UPDATE)
    op.execute(_CREATE_NO_DELETE)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TRIGGER IF EXISTS trg_device_events_no_delete")
    op.execute("DROP TRIGGER IF EXISTS trg_device_events_no_update")
    with op.batch_alter_table("checkouts", recreate="always") as batch_op:
        batch_op.drop_constraint("ck_checkouts_returned_closed_reason", type_="check")
