"""add courier vehicle fields and check constraint

Revision ID: 0002_add_courier_fields_and_constraint
Revises: None
Create Date: 2026-02-04 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0002_add_courier_fields_and_constraint'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add columns
    op.add_column('users', sa.Column('vehicle_type', sa.String(length=50), nullable=True))
    op.add_column('users', sa.Column('plate_number', sa.String(length=20), nullable=True))

    # Add CHECK constraint: if role == 'courier' then both fields must be non-null
    op.create_check_constraint(
        'ck_courier_vehicle_required',
        'users',
        "(role != 'courier') OR (vehicle_type IS NOT NULL AND plate_number IS NOT NULL)"
    )


def downgrade():
    # Drop constraint then columns
    op.drop_constraint('ck_courier_vehicle_required', 'users', type_='check')
    op.drop_column('users', 'plate_number')
    op.drop_column('users', 'vehicle_type')
