"""add asset config

Revision ID: 56499a75c3c6
Revises: c915540f60cb
Create Date: 2019-08-26 14:41:05.786454

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '56499a75c3c6'
down_revision = 'c915540f60cb'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('asset', schema=None) as batch_op:
        batch_op.add_column(sa.Column('file_config', sa.Unicode(), nullable=True))


def downgrade():
    with op.batch_alter_table('asset', schema=None) as batch_op:
        batch_op.drop_column('file_config')
