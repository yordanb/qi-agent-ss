"""add_role_and_is_active columns to users table

Revision ID: 9dbf1a3ca735
Revises: ad2b5009e4bc
Create Date: 2026-06-30 19:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '9dbf1a3ca735'
down_revision: Union[str, Sequence[str], None] = 'ad2b5009e4bc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add role column (nullable initially to backfill)
    op.add_column('users',
        sa.Column('role', sa.String(20), nullable=True),
        schema='tb_ss',
    )
    # Add is_active column
    op.add_column('users',
        sa.Column('is_active', sa.Boolean(), nullable=True),
        schema='tb_ss',
    )

    # Backfill: migrate is_admin data to role
    op.execute(
        "UPDATE tb_ss.users SET role = 'admin' WHERE is_admin = TRUE"
    )
    op.execute(
        "UPDATE tb_ss.users SET role = 'user' WHERE role IS NULL"
    )
    # Set all existing users active
    op.execute(
        "UPDATE tb_ss.users SET is_active = TRUE WHERE is_active IS NULL"
    )

    # Make columns NOT NULL now
    op.alter_column('users', 'role',
        existing_type=sa.String(20),
        nullable=False,
        schema='tb_ss',
    )
    op.alter_column('users', 'is_active',
        existing_type=sa.Boolean(),
        nullable=False,
        schema='tb_ss',
    )

    # Drop old is_admin column
    op.drop_column('users', 'is_admin', schema='tb_ss')


def downgrade() -> None:
    # Add back is_admin
    op.add_column('users',
        sa.Column('is_admin', sa.Boolean(), nullable=True),
        schema='tb_ss',
    )
    # Backfill is_admin based on role
    op.execute(
        "UPDATE tb_ss.users SET is_admin = TRUE WHERE role = 'admin'"
    )
    op.execute(
        "UPDATE tb_ss.users SET is_admin = FALSE WHERE role != 'admin'"
    )
    # Make is_admin NOT NULL
    op.alter_column('users', 'is_admin',
        existing_type=sa.Boolean(),
        nullable=False,
        schema='tb_ss',
    )
    # Drop new columns
    op.drop_column('users', 'is_active', schema='tb_ss')
    op.drop_column('users', 'role', schema='tb_ss')
