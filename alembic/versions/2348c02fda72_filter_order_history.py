"""Filter/order history

Revision ID: 2348c02fda72
Revises: 279b6709d0c0
Create Date: 2016-12-23 18:10:45.062192

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '2348c02fda72'
down_revision = '279b6709d0c0'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('equipment_family', schema=None) as batch_op:
        batch_op.alter_column('family_id', existing_type=sa.Unicode(), nullable=False)
        batch_op.alter_column('model', existing_type=sa.Unicode(), nullable=False)
        batch_op.create_unique_constraint(batch_op.f('uq_equipment_family_family_id'), ['family_id'])
        batch_op.create_unique_constraint(batch_op.f('uq_equipment_family_model'), ['model'])

    with op.batch_alter_table('event', schema=None) as batch_op:
        batch_op.add_column(sa.Column('event_id', sa.Unicode(), nullable=False))
        batch_op.add_column(sa.Column('removed', sa.Boolean(), nullable=False))
        batch_op.add_column(sa.Column('removed_date', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('remover_alias', sa.Unicode(), nullable=True))
        batch_op.add_column(sa.Column('remover_id', sa.Unicode(), nullable=True))
        batch_op.alter_column('creator_alias', existing_type=sa.Unicode(), nullable=False)
        batch_op.alter_column('creator_id', existing_type=sa.Unicode(), nullable=False)
        batch_op.create_unique_constraint(batch_op.f('uq_event_event_id'), ['event_id'])

    with op.batch_alter_table('event_status', schema=None) as batch_op:
        batch_op.alter_column('label', existing_type=sa.Unicode(), nullable=False)
        batch_op.alter_column('position', existing_type=sa.Integer(), nullable=False)
        batch_op.alter_column('status_id', existing_type=sa.Unicode(), nullable=False)
        batch_op.create_unique_constraint(batch_op.f('uq_event_status_label'), ['label'])
        batch_op.create_unique_constraint(batch_op.f('uq_event_status_position'), ['position'])
        batch_op.create_unique_constraint(batch_op.f('uq_event_status_status_id'), ['status_id'])


def downgrade():
    with op.batch_alter_table('event_status', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('uq_event_status_status_id'), type_='unique')
        batch_op.drop_constraint(batch_op.f('uq_event_status_position'), type_='unique')
        batch_op.drop_constraint(batch_op.f('uq_event_status_label'), type_='unique')
        batch_op.alter_column('status_id', existing_type=sa.Unicode(), nullable=True)
        batch_op.alter_column('position', existing_type=sa.Integer(), nullable=True)
        batch_op.alter_column('label', existing_type=sa.Unicode(), nullable=True)

    with op.batch_alter_table('event', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('uq_event_event_id'), type_='unique')
        batch_op.alter_column('creator_id', existing_type=sa.Unicode(), nullable=True)
        batch_op.alter_column('creator_alias', existing_type=sa.Unicode(), nullable=True)
        batch_op.drop_column('remover_id')
        batch_op.drop_column('remover_alias')
        batch_op.drop_column('removed_date')
        batch_op.drop_column('removed')
        batch_op.drop_column('event_id')

    with op.batch_alter_table('equipment_family', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('uq_equipment_family_model'), type_='unique')
        batch_op.drop_constraint(batch_op.f('uq_equipment_family_family_id'), type_='unique')
        batch_op.alter_column('model', existing_type=sa.Unicode(), nullable=True)
        batch_op.alter_column('family_id', existing_type=sa.Unicode(), nullable=True)
