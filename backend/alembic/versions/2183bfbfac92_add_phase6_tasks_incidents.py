"""add_phase6_tasks_incidents

Revision ID: 2183bfbfac92
Revises: 25b5f5fa18e7
Create Date: 2026-06-10 04:06:19.864220
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '2183bfbfac92'
down_revision = '25b5f5fa18e7'
branch_labels = None
depends_on = None

def upgrade():
    op.execute("""DO $$ BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'incidentstatus') THEN
            CREATE TYPE incidentstatus AS ENUM ('OPEN', 'ACKNOWLEDGED', 'RESOLVED', 'CLOSED');
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'incidentseverity') THEN
            CREATE TYPE incidentseverity AS ENUM ('INFO', 'CAUTION', 'WARNING', 'CRITICAL');
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'taskpriority') THEN
            CREATE TYPE taskpriority AS ENUM ('LOW', 'MEDIUM', 'HIGH', 'URGENT');
        END IF;
    END $$;""")

    # incidents - add new columns (nullable to handle existing rows)
    op.add_column('incidents', sa.Column('status', sa.String(), nullable=True))
    op.execute("UPDATE incidents SET status = 'OPEN' WHERE status IS NULL")
    op.add_column('incidents', sa.Column('stay_id', sa.String(), nullable=True))
    op.add_column('incidents', sa.Column('assigned_to', sa.String(), nullable=True))
    op.add_column('incidents', sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('incidents', sa.Column('location_description', sa.String(), nullable=True))
    op.add_column('incidents', sa.Column('witness_names', sa.Text(), nullable=True))
    op.add_column('incidents', sa.Column('immediate_action_taken', sa.Text(), nullable=True))
    op.add_column('incidents', sa.Column('follow_up_required', sa.Boolean(), nullable=True))
    op.add_column('incidents', sa.Column('follow_up_notes', sa.Text(), nullable=True))
    op.add_column('incidents', sa.Column('acknowledged_by', sa.String(), nullable=True))
    op.add_column('incidents', sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('incidents', sa.Column('resolved_by', sa.String(), nullable=True))
    op.execute("ALTER TABLE incidents ALTER COLUMN organization_id SET NOT NULL")
    op.execute("ALTER TABLE incidents ALTER COLUMN severity TYPE incidentseverity USING severity::incidentseverity")
    op.create_index(op.f('ix_incidents_dog_id'), 'incidents', ['dog_id'], unique=False)

    # tasks - add new columns
    op.add_column('tasks', sa.Column('priority', sa.String(), nullable=True))
    op.execute("UPDATE tasks SET priority = 'MEDIUM' WHERE priority IS NULL")
    op.add_column('tasks', sa.Column('created_by', sa.String(), nullable=True))
    op.add_column('tasks', sa.Column('dog_id', sa.String(), nullable=True))
    op.add_column('tasks', sa.Column('stay_id', sa.String(), nullable=True))
    op.add_column('tasks', sa.Column('checklist', sa.JSON(), nullable=True))
    op.add_column('tasks', sa.Column('recurrence', sa.String(), nullable=True))
    op.add_column('tasks', sa.Column('tags', sa.JSON(), nullable=True))
    op.execute("ALTER TABLE tasks ALTER COLUMN organization_id SET NOT NULL")
    op.create_index(op.f('ix_tasks_assigned_to'), 'tasks', ['assigned_to'], unique=False)
    op.create_index(op.f('ix_tasks_dog_id'), 'tasks', ['dog_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_tasks_dog_id'), table_name='tasks')
    op.drop_index(op.f('ix_tasks_assigned_to'), table_name='tasks')
    op.drop_column('tasks', 'tags')
    op.drop_column('tasks', 'recurrence')
    op.drop_column('tasks', 'checklist')
    op.drop_column('tasks', 'stay_id')
    op.drop_column('tasks', 'dog_id')
    op.drop_column('tasks', 'created_by')
    op.drop_column('tasks', 'priority')
    op.drop_index(op.f('ix_incidents_dog_id'), table_name='incidents')
    op.drop_column('incidents', 'resolved_by')
    op.drop_column('incidents', 'acknowledged_at')
    op.drop_column('incidents', 'acknowledged_by')
    op.drop_column('incidents', 'follow_up_notes')
    op.drop_column('incidents', 'follow_up_required')
    op.drop_column('incidents', 'immediate_action_taken')
    op.drop_column('incidents', 'witness_names')
    op.drop_column('incidents', 'location_description')
    op.drop_column('incidents', 'occurred_at')
    op.drop_column('incidents', 'assigned_to')
    op.drop_column('incidents', 'stay_id')
    op.drop_column('incidents', 'status')
