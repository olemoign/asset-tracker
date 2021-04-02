"""Add status_type

Revision ID: 80c54335e8c0
Revises: c915540f60cb
Create Date: 2019-12-16 11:21:19.544960

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '80c54335e8c0'
down_revision = 'c915540f60cb'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('event_status', schema=None) as batch_op:
        batch_op.add_column(sa.Column('status_type', sa.Unicode(), nullable=True, server_default='event'))


def downgrade():
    with op.batch_alter_table('event_status', schema=None) as batch_op:
        batch_op.drop_column('status_type')
