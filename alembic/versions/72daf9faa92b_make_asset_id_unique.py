"""Make asset_id unique

Revision ID: 72daf9faa92b
Revises: 49e3635c66c5
Create Date: 2017-10-10 14:23:25.072297

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = '72daf9faa92b'
down_revision = '49e3635c66c5'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('asset', schema=None) as batch_op:
        batch_op.create_unique_constraint(batch_op.f('uq_asset_asset_id'), ['asset_id'])


def downgrade():
    with op.batch_alter_table('asset', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('uq_asset_asset_id'), type_='unique')
