"""add consumable and consumable family

Revision ID: ea12469de59d
Revises: 80c54335e8c0
Create Date: 2019-12-18 19:19:12.054826

"""

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = 'ea12469de59d'
down_revision = '80c54335e8c0'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'consumable_family',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('family_id', sa.Integer(), nullable=True),
        sa.Column('model', sa.Unicode(), nullable=True),
        sa.Column('equipment_family_id', sa.Integer, nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_consumable_family')),
        sa.ForeignKeyConstraint(['equipment_family_id'], ['equipment_family.id'],
                                name=op.f('fk_consumable_equipment_family_id_equipment_family')),
    )

    op.create_table(
        'consumable',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('family_id', sa.Integer(), nullable=True),
        sa.Column('equipment_id', sa.Integer(), nullable=True),
        sa.Column('expiration_date', sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(['equipment_id'], ['equipment.id'], name=op.f('fk_consumable_equipment_id_equipment')),
        sa.ForeignKeyConstraint(
            ['family_id'], ['consumable_family.id'], name=op.f('fk_consumable_family_id_consumable_family')
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_consumable')),
    )


def downgrade():
    op.drop_table('consumable_family')
    op.drop_table('consumable')
