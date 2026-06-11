"""add_dog_notes_minio

Revision ID: 45d88da142dd
Revises: 2183bfbfac92
Create Date: 2026-06-11 01:18:10.192991
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '45d88da142dd'
down_revision = '2183bfbfac92'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('dog_notes',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('organization_id', sa.String(), nullable=False),
    sa.Column('dog_id', sa.String(), nullable=False),
    sa.Column('note_text', sa.String(length=500), nullable=False),
    sa.Column('is_alert', sa.Boolean(), nullable=True),
    sa.Column('image_keys', sa.JSON(), nullable=True),
    sa.Column('created_by', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['dog_id'], ['dogs.id'], ),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_dog_notes_dog_id'), 'dog_notes', ['dog_id'], unique=False)
    op.create_index(op.f('ix_dog_notes_organization_id'), 'dog_notes', ['organization_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_dog_notes_organization_id'), table_name='dog_notes')
    op.drop_index(op.f('ix_dog_notes_dog_id'), table_name='dog_notes')
    op.drop_table('dog_notes')
