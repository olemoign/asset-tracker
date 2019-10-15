"""0.9

Revision ID: e48836ce2279
Revises:
Create Date: 2016-06-13 16:10:42.694244

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'e48836ce2279'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'asset',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('tenant_id', sa.Unicode(), nullable=True),
        sa.Column('asset_id', sa.Unicode(), nullable=True),
        sa.Column('customer_id', sa.Unicode(), nullable=True),
        sa.Column('customer_name', sa.Unicode(), nullable=True),
        sa.Column('site', sa.Unicode(), nullable=True),
        sa.Column('current_location', sa.Unicode(), nullable=True),
        sa.Column('notes', sa.Unicode(), nullable=True),
        sa.Column('next_calibration', sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_asset')),
    )

    op.create_table(
        'equipment_family',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('model', sa.Unicode(), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_equipment_family')),
    )

    op.create_table(
        'equipment',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('family_id', sa.Integer(), nullable=True),
        sa.Column('asset_id', sa.Integer(), nullable=True),
        sa.Column('serial_number', sa.Unicode(), nullable=True),
        sa.ForeignKeyConstraint(['asset_id'], ['asset.id'], name=op.f('fk_equipment_asset_id_asset')),
        sa.ForeignKeyConstraint(
            ['family_id'], ['equipment_family.id'], name=op.f('fk_equipment_family_id_equipment_family')
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_equipment')),
    )

    op.create_table(
        'event',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=True),
        sa.Column('date', sa.DateTime(), nullable=True),
        sa.Column('creator_id', sa.Integer(), nullable=True),
        sa.Column('creator_alias', sa.Unicode(), nullable=True),
        sa.Column(
            'status',
            sa.Enum('service', 'repair', 'calibration', 'transit_parsys', 'transit_customer', name='status'),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(['asset_id'], ['asset.id'], name=op.f('fk_event_asset_id_asset')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_event')),
    )


def downgrade():
    op.drop_table('event')
    op.drop_table('equipment')
    op.drop_table('equipment_family')
    op.drop_table('asset')
