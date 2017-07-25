"""Remove next calibration

Revision ID: c1048d8d385e
Revises: 20d6bddc809a
Create Date: 2016-12-05 12:05:03.744766

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c1048d8d385e'
down_revision = '20d6bddc809a'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('asset', schema=None) as batch_op:
        batch_op.alter_column('asset_id', existing_type=sa.Unicode(), nullable=False)
        batch_op.alter_column('tenant_id', existing_type=sa.Unicode(), nullable=False)
        batch_op.drop_column('next_calibration')


def downgrade():
    with op.batch_alter_table('asset', schema=None) as batch_op:
        batch_op.add_column(sa.Column('next_calibration', sa.Date(), nullable=True))
        batch_op.alter_column('tenant_id', existing_type=sa.Unicode(), nullable=True)
        batch_op.alter_column('asset_id', existing_type=sa.Unicode(), nullable=True)
