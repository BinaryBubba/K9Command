"""fix_dogs_household_fk

Revision ID: a141ced0c87a
Revises: 965814446b33
Create Date: 2026-06-08
"""
from alembic import op
import sqlalchemy as sa

revision = 'a141ced0c87a'
down_revision = '965814446b33'
branch_labels = None
depends_on = None

def upgrade():
    # Drop the old FK that points dogs.household_id -> users.household_id
    op.drop_constraint('dogs_household_id_fkey', 'dogs', type_='foreignkey')
    # Add correct FK: dogs.household_id -> households.id
    op.create_foreign_key(
        'dogs_household_id_fkey',
        'dogs', 'households',
        ['household_id'], ['id']
    )

def downgrade():
    op.drop_constraint('dogs_household_id_fkey', 'dogs', type_='foreignkey')
    op.create_foreign_key(
        'dogs_household_id_fkey',
        'dogs', 'users',
        ['household_id'], ['household_id']
    )
