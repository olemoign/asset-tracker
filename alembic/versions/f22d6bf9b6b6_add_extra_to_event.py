"""add extra to Event

Revision ID: f22d6bf9b6b6
Revises: cd58dc1487e1
Create Date: 2017-08-29 19:21:41.214271

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f22d6bf9b6b6'
down_revision = 'cd58dc1487e1'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('asset', schema=None) as batch_op:
        batch_op.drop_column('software_version')

    with op.batch_alter_table('event', schema=None) as batch_op:
        batch_op.add_column(sa.Column('extra', sa.Unicode(), nullable=True))


def downgrade():
    with op.batch_alter_table('event', schema=None) as batch_op:
        batch_op.drop_column('extra')

    with op.batch_alter_table('asset', schema=None) as batch_op:
        batch_op.add_column(sa.Column('software_version', sa.VARCHAR(), nullable=True))
