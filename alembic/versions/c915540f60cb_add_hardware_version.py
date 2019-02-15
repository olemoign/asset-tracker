"""Add hardware version

Revision ID: c915540f60cb
Revises: 70292af6fd9e
Create Date: 2019-02-15 15:15:58.463903

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'c915540f60cb'
down_revision = '70292af6fd9e'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('asset', schema=None) as batch_op:
        batch_op.add_column(sa.Column('hardware_version', sa.Unicode(), nullable=True))


def downgrade():
    with op.batch_alter_table('asset', schema=None) as batch_op:
        batch_op.drop_column('hardware_version')
