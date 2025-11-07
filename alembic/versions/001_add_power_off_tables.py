"""Add power-off task tables

Revision ID: 001_add_power_off_tables
Revises: 
Create Date: 2025-11-05 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '001_add_power_off_tables'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create power_off_tasks table
    op.create_table('power_off_tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('booking_id', sa.Integer(), nullable=False),
        sa.Column('room_id', sa.Integer(), nullable=False),
        sa.Column('scheduled_time', sa.DateTime(), nullable=False),
        sa.Column('executed_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.Enum('pending', 'scheduled', 'completed', 'failed', 'cancelled', name='power_off_task_status'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_power_off_tasks_booking_id', 'booking_id'),
        sa.Index('idx_power_off_tasks_room_id', 'room_id'),
        sa.Index('idx_power_off_tasks_status', 'status'),
        sa.Index('idx_power_off_tasks_scheduled_time', 'scheduled_time')
    )
    
    # Create power_off_audit_log table
    op.create_table('power_off_audit_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('booking_id', sa.Integer(), nullable=False),
        sa.Column('room_id', sa.Integer(), nullable=False),
        sa.Column('operation_type', sa.String(length=50), nullable=False),
        sa.Column('result', sa.String(length=20), nullable=False),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_power_off_audit_log_booking_id', 'booking_id'),
        sa.Index('idx_power_off_audit_log_room_id', 'room_id'),
        sa.Index('idx_power_off_audit_log_created_at', 'created_at')
    )


def downgrade():
    op.drop_table('power_off_audit_log')
    op.drop_table('power_off_tasks')