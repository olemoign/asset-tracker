"""add data to Event

Revision ID: 98040f2be9fd
Revises: 843bfa914d35
Create Date: 2017-08-23 13:17:56.629772

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '98040f2be9fd'
down_revision = '843bfa914d35'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('asset', schema=None) as batch_op:
        batch_op.drop_column('software_version')

    with op.batch_alter_table('event', schema=None) as batch_op:
        batch_op.add_column(sa.Column('data', sa.Unicode(), nullable=True))


def downgrade():
    with op.batch_alter_table('event', schema=None) as batch_op:
        batch_op.drop_column('data')

    with op.batch_alter_table('asset', schema=None) as batch_op:
        batch_op.add_column(sa.Column('software_version', sa.VARCHAR(), nullable=True))
