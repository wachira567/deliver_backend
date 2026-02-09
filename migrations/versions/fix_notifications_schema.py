"""fix notifications schema mismatch

Revision ID: fix_notifications_schema
Revises: 5be11687e9ca
Create Date: 2026-02-06 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fix_notifications_schema'
down_revision = '5be11687e9ca'
branch_labels = None
depends_on = None


def upgrade():
    # Fix the notifications table schema mismatch
    # The original migration created is_read as DateTime instead of Boolean
    # and was missing the read_at column entirely
    
    with op.batch_alter_table('notifications', schema=None) as batch_op:
        # Drop the incorrectly typed is_read column (DateTime -> Boolean)
        batch_op.drop_column('is_read')
        
        # Add the correct is_read column as Boolean
        batch_op.add_column(sa.Column('is_read', sa.Boolean(), nullable=True))
        
        # Add the missing read_at column
        batch_op.add_column(sa.Column('read_at', sa.DateTime(), nullable=True))


def downgrade():
    # Revert the changes
    with op.batch_alter_table('notifications', schema=None) as batch_op:
        # Drop read_at column
        batch_op.drop_column('read_at')
        
        # Drop the Boolean is_read column
        batch_op.drop_column('is_read')
        
        # Recreate the original DateTime is_read column
        batch_op.add_column(sa.Column('is_read', sa.DateTime(), nullable=True))

