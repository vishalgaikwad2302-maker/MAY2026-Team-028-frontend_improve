"""0005 transparency post images and optional complaint

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-03 11:00:00.000000+00:00

Makes ``transparency_posts.complaint_id`` nullable with non-unique index so
general community updates can be published without an attached complaint.
Adds ``images`` (JSON) to store up to 3 image URLs.
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0005'
down_revision: str | None = '0004'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply the change."""
    with op.batch_alter_table('transparency_posts', schema=None) as batch_op:
        batch_op.drop_index('ix_transparency_posts_complaint_id')
        batch_op.alter_column('complaint_id', existing_type=sa.Integer(), nullable=True)
        batch_op.create_index('ix_transparency_posts_complaint_id', ['complaint_id'], unique=False)
        batch_op.add_column(sa.Column('images', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Reverse the change."""
    # Ensure no rows have null complaint_id before re-applying NOT NULL constraint
    op.execute("DELETE FROM transparency_posts WHERE complaint_id IS NULL")
    with op.batch_alter_table('transparency_posts', schema=None) as batch_op:
        batch_op.drop_column('images')
        batch_op.drop_index('ix_transparency_posts_complaint_id')
        batch_op.alter_column('complaint_id', existing_type=sa.Integer(), nullable=False)
        batch_op.create_index('ix_transparency_posts_complaint_id', ['complaint_id'], unique=True)
