"""Remove asset.calibration_next

Revision ID: 40967a8ed62c
Revises: 083c623dbc61
Create Date: 2021-02-02 22:47:02.263158

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '40967a8ed62c'
down_revision = '083c623dbc61'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('asset', schema=None) as batch_op:
        batch_op.drop_column('calibration_next')


def downgrade():
    with op.batch_alter_table('asset', schema=None) as batch_op:
        batch_op.add_column(sa.Column('calibration_next', sa.Date(), autoincrement=False, nullable=True))
