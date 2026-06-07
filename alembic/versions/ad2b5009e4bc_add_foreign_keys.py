"""add foreign keys

Revision ID: ad2b5009e4bc
Revises: c65b3ffbbdbf
Create Date: 2026-06-07

"""
from alembic import op

revision = 'ad2b5009e4bc'
down_revision = 'c65b3ffbbdbf'
branch_labels = None
depends_on = None

def upgrade():
    op.create_foreign_key('fk_ss_records_nrp', 'ss_records', 'users', ['nrp'], ['nrp'], ondelete='SET NULL', schema='tb_ss')
    op.create_foreign_key('fk_ss_records_import', 'ss_records', 'import_log', ['latest_import_id'], ['id'], ondelete='SET NULL', schema='tb_ss')
    op.create_foreign_key('fk_manpower_nrp', 'manpower', 'users', ['nrp'], ['nrp'], ondelete='SET NULL', schema='tb_ss')
    op.create_foreign_key('fk_refresh_tokens_nrp', 'refresh_tokens', 'users', ['nrp'], ['nrp'], ondelete='CASCADE', schema='tb_ss')

def downgrade():
    op.drop_constraint('fk_ss_records_nrp', 'ss_records', schema='tb_ss', type_='foreignkey')
    op.drop_constraint('fk_ss_records_import', 'ss_records', schema='tb_ss', type_='foreignkey')
    op.drop_constraint('fk_manpower_nrp', 'manpower', schema='tb_ss', type_='foreignkey')
    op.drop_constraint('fk_refresh_tokens_nrp', 'refresh_tokens', schema='tb_ss', type_='foreignkey')
