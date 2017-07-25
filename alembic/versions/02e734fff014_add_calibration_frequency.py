"""Add calibration frequency

Revision ID: 02e734fff014
Revises: c8984e73a5de
Create Date: 2017-02-27 19:33:22.012970

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '02e734fff014'
down_revision = 'c8984e73a5de'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('asset', schema=None) as batch_op:
        batch_op.add_column(sa.Column('calibration_frequency', sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table('asset', schema=None) as batch_op:
        batch_op.drop_column('calibration_frequency')
