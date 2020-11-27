"""Add tenant_name

Revision ID: e8996138f616
Revises: 083c623dbc61
Create Date: 2020-11-27 22:36:40.796306

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e8996138f616'
down_revision = '083c623dbc61'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('asset', schema=None) as batch_op:
        batch_op.add_column(sa.Column('tenant_name', sa.Unicode(), nullable=False, server_default='Fix this'))

    with op.batch_alter_table('consumable_families_equipment_families', schema=None) as batch_op:
        batch_op.alter_column('consumable_family_id', existing_type=sa.Integer(), nullable=False)
        batch_op.alter_column('equipment_family_id', existing_type=sa.Integer(), nullable=False)
        batch_op.create_unique_constraint(
            batch_op.f('uq_consumable_families_equipment_families_consumable_family_id'),
            ['consumable_family_id', 'equipment_family_id'],
        )

    with op.batch_alter_table('consumable_family', schema=None) as batch_op:
        batch_op.create_unique_constraint(batch_op.f('uq_consumable_family_family_id'), ['family_id'])
        batch_op.create_unique_constraint(batch_op.f('uq_consumable_family_model'), ['model'])

    with op.batch_alter_table('equipment', schema=None) as batch_op:
        batch_op.alter_column('family_id', existing_type=sa.Integer(), nullable=False)

    with op.batch_alter_table('site', schema=None) as batch_op:
        batch_op.add_column(sa.Column('tenant_name', sa.Unicode(), nullable=False, server_default='Fix this'))


def downgrade():
    with op.batch_alter_table('site', schema=None) as batch_op:
        batch_op.drop_column('tenant_name')

    with op.batch_alter_table('equipment', schema=None) as batch_op:
        batch_op.alter_column('family_id', existing_type=sa.Integer(), nullable=True)

    with op.batch_alter_table('consumable_family', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('uq_consumable_family_model'), type_='unique')
        batch_op.drop_constraint(batch_op.f('uq_consumable_family_family_id'), type_='unique')

    with op.batch_alter_table('consumable_families_equipment_families', schema=None) as batch_op:
        batch_op.drop_constraint(
            batch_op.f('uq_consumable_families_equipment_families_consumable_family_id'), type_='unique'
        )
        batch_op.alter_column('equipment_family_id', existing_type=sa.Integer(), nullable=True)
        batch_op.alter_column('consumable_family_id', existing_type=sa.Integer(), nullable=True)

    with op.batch_alter_table('asset', schema=None) as batch_op:
        batch_op.drop_column('tenant_name')
