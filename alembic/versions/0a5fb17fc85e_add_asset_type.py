"""Add asset type

Revision ID: 0a5fb17fc85e
Revises: 2348c02fda72
Create Date: 2017-01-04 11:37:17.929430

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '0a5fb17fc85e'
down_revision = '2348c02fda72'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('asset', schema=None) as batch_op:
        batch_op.add_column(sa.Column('type', sa.Unicode(), nullable=True))


def downgrade():
    with op.batch_alter_table('asset', schema=None) as batch_op:
        batch_op.drop_column('type')
