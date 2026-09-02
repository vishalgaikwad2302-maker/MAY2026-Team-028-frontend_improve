"""0004 drop bulk_pickup fee

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-11 19:00:00.000000+00:00

Drops ``bulk_pickups.fee``: this is a municipality-run, no-payment service, so
there is no fee/pricing concept on the backend. The column was carried over
from the frontend mock (``BulkPickupContext.jsx``) when the model was first
authored, but nothing computes or charges it server-side.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0004'
down_revision: str | None = '0003'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply the change."""
    with op.batch_alter_table('bulk_pickups', schema=None) as batch_op:
        batch_op.drop_column('fee')


def downgrade() -> None:
    """Reverse the change."""
    with op.batch_alter_table('bulk_pickups', schema=None) as batch_op:
        batch_op.add_column(sa.Column('fee', sa.Float(), nullable=False, server_default='0'))
