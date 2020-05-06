"""Remove equipment expiration dates

Revision ID: 199b80115867
Revises: ea12469de59d
Create Date: 2019-12-19 18:05:59.102503

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '199b80115867'
down_revision = 'ea12469de59d'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('equipment', schema=None) as batch_op:
        batch_op.drop_column('expiration_date_1')
        batch_op.drop_column('expiration_date_2')


def downgrade():
    with op.batch_alter_table('equipment', schema=None) as batch_op:
        batch_op.add_column(sa.Column('expiration_date_1', sa.Date(), nullable=True))
        batch_op.add_column(sa.Column('expiration_date_2', sa.Date(), nullable=True))
