"""site_id must never be null

Revision ID: 5987feade5e7
Revises: 70292af6fd9e
Create Date: 2018-07-17 15:45:12.982494

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = '5987feade5e7'
down_revision = '70292af6fd9e'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('site', schema=None) as batch_op:
        batch_op.alter_column('site_id', nullable=False)


def downgrade():
    with op.batch_alter_table('site', schema=None) as batch_op:
        batch_op.alter_column('site_id', nullable=True)
