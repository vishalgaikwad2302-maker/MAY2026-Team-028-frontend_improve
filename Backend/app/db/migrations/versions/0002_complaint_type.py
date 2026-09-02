"""0002 complaint type

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-09 00:00:00+00:00

Adds the nullable `complaint_type` column used by S2-A18 to classify a
complaint as overflow / delay / extra_collection, independent of the
existing `category` (hazard classification) column. Nullable + no default
means existing rows are unaffected and no backfill is required.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: str | None = '0001'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply the change."""
    with op.batch_alter_table('complaints', schema=None) as batch_op:
        batch_op.add_column(sa.Column('complaint_type', sa.String(length=50), nullable=True))
        batch_op.create_index(
            batch_op.f('ix_complaints_complaint_type'), ['complaint_type'], unique=False
        )


def downgrade() -> None:
    """Reverse the change."""
    with op.batch_alter_table('complaints', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_complaints_complaint_type'))
        batch_op.drop_column('complaint_type')
