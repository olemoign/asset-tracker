"""Add_consumable_families_equipment_families_

Revision ID: 083c623dbc61
Revises: 199b80115867
Create Date: 2020-01-16 17:16:11.167896

"""

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = '083c623dbc61'
down_revision = '199b80115867'
branch_labels = None
depends_on = None


# noinspection PyTypeChecker
def upgrade():
    with op.batch_alter_table('consumable_family', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_consumable_equipment_family_id_equipment_family'), type_='foreignkey')
        batch_op.drop_column('equipment_family_id')

    op.create_table(
        'consumable_families_equipment_families',
        sa.Column('consumable_family_id', sa.Integer(), nullable=True),
        sa.Column('equipment_family_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ['consumable_family_id'],
            ['consumable_family.id'],
            name=op.f('fk_consumable_families_equipment_families_consumable_family_id_consumable_family'),
        ),
        sa.ForeignKeyConstraint(
            ['equipment_family_id'],
            ['equipment_family.id'],
            name=op.f('fk_consumable_families_equipment_families_equipment_family_id_equipment_family'),
        ),
    )


def downgrade():
    op.drop_table('consumable_families_equipment_families')

    with op.batch_alter_table('consumable_family', schema=None) as batch_op:
        batch_op.add_column(sa.Column('equipment_family_id', sa.Integer, nullable=True))
        batch_op.create_foreign_key(batch_op.f('fk_consumable_equipment_family_id_equipment_family'),
                                    'equipment_family', ['equipment_family_id'], ['id'])
