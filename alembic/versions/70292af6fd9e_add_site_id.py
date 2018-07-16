"""add site_id

Revision ID: 70292af6fd9e
Revises: 72daf9faa92b
Create Date: 2018-07-16 12:05:18.423951

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '70292af6fd9e'
down_revision = '72daf9faa92b'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('site', schema=None) as batch_op:
        batch_op.add_column(sa.Column('site_id', sa.Unicode()))
        batch_op.create_unique_constraint(batch_op.f('uq_site_site_id'), ['site_id'])


def downgrade():
    with op.batch_alter_table('site', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('uq_site_site_id'), type_='unique')
        batch_op.drop_column('site_id')
