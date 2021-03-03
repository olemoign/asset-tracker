"""Add status.label_marlink

Revision ID: 6715e132d14a
Revises: 52f92ee869a0
Create Date: 2021-03-03 21:41:53.461934

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '6715e132d14a'
down_revision = '52f92ee869a0'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('event_status', schema=None) as batch_op:
        batch_op.add_column(sa.Column('label_marlink', sa.Unicode(), nullable=True))
        batch_op.create_unique_constraint(batch_op.f('uq_event_status_label_marlink'), ['label_marlink'])


def downgrade():
    with op.batch_alter_table('event_status', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('uq_event_status_label_marlink'), type_='unique')
        batch_op.drop_column('label_marlink')
