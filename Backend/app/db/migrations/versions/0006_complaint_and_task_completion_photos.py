"""0006 complaint and task completion photos

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-03 13:00:00.000000+00:00

Adds ``completion_photos`` (JSON) and ``resolution_notes`` (Text) to ``complaints`` table.
Adds ``completion_photos`` (JSON) to ``tasks`` table.
Allows crew members to attach 1-3 proof-of-work photos when marking a case resolved.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0006'
down_revision: str | None = '0005'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add completion_photos and resolution_notes columns."""
    with op.batch_alter_table('complaints', schema=None) as batch_op:
        batch_op.add_column(sa.Column('completion_photos', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('resolution_notes', sa.Text(), nullable=True))

    with op.batch_alter_table('tasks', schema=None) as batch_op:
        batch_op.add_column(sa.Column('completion_photos', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Reverse completion_photos and resolution_notes additions."""
    with op.batch_alter_table('tasks', schema=None) as batch_op:
        batch_op.drop_column('completion_photos')

    with op.batch_alter_table('complaints', schema=None) as batch_op:
        batch_op.drop_column('resolution_notes')
        batch_op.drop_column('completion_photos')
