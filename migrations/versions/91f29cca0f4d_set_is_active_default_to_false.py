"""set is_active default to false

Revision ID: 91f29cca0f4d
Revises: 4607158353dd
Create Date: 2026-09-27 17:04:02.326314

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '91f29cca0f4d'
down_revision: Union[str, Sequence[str], None] = '4607158353dd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column('users', 'is_active',
               existing_type=sa.BOOLEAN(),
               server_default=sa.text('false'),
               existing_nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('users', 'is_active',
               existing_type=sa.BOOLEAN(),
               server_default=sa.text('true'),
               existing_nullable=False)
