"""Status and calibration_next as columns

Revision ID: c8984e73a5de
Revises: 0a5fb17fc85e
Create Date: 2017-01-31 15:28:31.638303

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'c8984e73a5de'
down_revision = '0a5fb17fc85e'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('asset', schema=None) as batch_op:
        batch_op.add_column(sa.Column('calibration_next', sa.Date(), nullable=True))
        batch_op.add_column(sa.Column('status_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(batch_op.f('fk_asset_status_id_event_status'),
                                    'event_status', ['status_id'], ['id'])

        batch_op.alter_column('type', new_column_name='asset_type', existing_type=sa.Unicode(), nullable=False)

    with op.batch_alter_table('event', schema=None) as batch_op:
        batch_op.alter_column('removed_date', new_column_name='removed_at')

        batch_op.alter_column('asset_id', existing_type=sa.Integer(), nullable=False)
        batch_op.alter_column('date', existing_type=sa.Date(), nullable=False)
        batch_op.alter_column('status_id', existing_type=sa.Integer(), nullable=False)

    with op.batch_alter_table('equipment', schema=None) as batch_op:
        batch_op.alter_column('asset_id', existing_type=sa.Integer(), nullable=False)


def downgrade():
    with op.batch_alter_table('asset', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_asset_status_id_event_status'), type_='foreignkey')
        batch_op.drop_column('calibration_next')
        batch_op.drop_column('status_id')

        batch_op.alter_column('asset_type', new_column_name='type', existing_type=sa.Unicode(), nullable=True)

    with op.batch_alter_table('event', schema=None) as batch_op:
        batch_op.alter_column('removed_at', new_column_name='removed_date')

        batch_op.alter_column('asset_id', existing_type=sa.Integer(), nullable=True)
        batch_op.alter_column('date', existing_type=sa.Date(), nullable=True)
        batch_op.alter_column('status_id', existing_type=sa.Integer(), nullable=True)

    with op.batch_alter_table('equipment', schema=None) as batch_op:
        batch_op.alter_column('asset_id', existing_type=sa.Integer(), nullable=True)
