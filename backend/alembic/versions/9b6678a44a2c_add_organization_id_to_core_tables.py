"""add_organization_id_to_core_tables

Revision ID: 9b6678a44a2c
Revises: 21b130e459bf
Create Date: 2026-06-08
"""
from alembic import op
import sqlalchemy as sa

revision = '9b6678a44a2c'
down_revision = '21b130e459bf'
branch_labels = None
depends_on = None

K9CC_ORG_ID = '00000000-0000-0000-0000-000000000001'

TABLES = [
    'users',
    'dogs',
    'bookings',
    'tasks',
    'incidents',
    'audit_logs',
    'locations',
]

def upgrade():
    for table in TABLES:
        op.add_column(table,
            sa.Column('organization_id', sa.String(), nullable=True)
        )
    for table in TABLES:
        op.execute(
            f"UPDATE {table} SET organization_id = '{K9CC_ORG_ID}' WHERE organization_id IS NULL"
        )
    for table in TABLES:
        op.create_foreign_key(
            f'fk_{table}_organization_id',
            table, 'organizations',
            ['organization_id'], ['id']
        )
    for table in TABLES:
        op.create_index(
            f'ix_{table}_organization_id',
            table, ['organization_id']
        )

def downgrade():
    for table in TABLES:
        op.drop_index(f'ix_{table}_organization_id', table_name=table)
        op.drop_constraint(f'fk_{table}_organization_id', table, type_='foreignkey')
        op.drop_column(table, 'organization_id')
