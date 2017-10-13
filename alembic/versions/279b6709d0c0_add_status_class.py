"""Add status class

Revision ID: 279b6709d0c0
Revises: c1048d8d385e
Create Date: 2016-12-16 19:04:18.344604

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '279b6709d0c0'
down_revision = 'c1048d8d385e'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'event_status',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('status_id', sa.Unicode(), nullable=True),
        sa.Column('position', sa.Integer(), nullable=True),
        sa.Column('label', sa.Unicode(), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_status'))
    )

    with op.batch_alter_table('equipment_family', schema=None) as batch_op:
        batch_op.add_column(sa.Column('family_id', sa.Unicode(), nullable=True))

    with op.batch_alter_table('event', schema=None) as batch_op:
        batch_op.add_column(sa.Column('created_at', sa.DateTime(), nullable=False))
        batch_op.add_column(sa.Column('status_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(batch_op.f('fk_event_status_id_event_status'), 'event_status', ['status_id'],
                                    ['id'])
        batch_op.drop_column('status')


def downgrade():
    with op.batch_alter_table('event', schema=None) as batch_op:
        batch_op.add_column(sa.Column('status', sa.Unicode(), nullable=True))
        batch_op.drop_constraint(batch_op.f('fk_event_status_id_event_status'), type_='foreignkey')
        batch_op.drop_column('status_id')
        batch_op.drop_column('created_at')

    with op.batch_alter_table('equipment_family', schema=None) as batch_op:
        batch_op.drop_column('family_id')

    op.drop_table('event_status')
