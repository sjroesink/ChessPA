"""add email and auth_provider to users

Revision ID: 357d17c50335
Revises: 9793b233d94c
Create Date: 2026-04-14 08:36:27.355195

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '357d17c50335'
down_revision: Union[str, Sequence[str], None] = '9793b233d94c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add email and auth_provider columns to users table."""
    op.add_column('users', sa.Column('email', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('auth_provider', sa.String(length=20), nullable=False, server_default='lichess'))
    op.create_unique_constraint('uq_users_email', 'users', ['email'])


def downgrade() -> None:
    """Remove email and auth_provider columns from users table."""
    op.drop_constraint('uq_users_email', 'users', type_='unique')
    op.drop_column('users', 'auth_provider')
    op.drop_column('users', 'email')
