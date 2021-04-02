"""Add expiration_date to Equipment

Revision ID: cd58dc1487e1
Revises: 843bfa914d35
Create Date: 2017-08-24 19:28:05.959882

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'cd58dc1487e1'
down_revision = '843bfa914d35'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('equipment', schema=None) as batch_op:
        batch_op.add_column(sa.Column('expiration_date_1', sa.Date(), nullable=True))
        batch_op.add_column(sa.Column('expiration_date_2', sa.Date(), nullable=True))

        batch_op.alter_column('family_id', existing_type=sa.Integer(), nullable=True)


def downgrade():
    with op.batch_alter_table('equipment', schema=None) as batch_op:
        batch_op.drop_column('expiration_date_2')
        batch_op.drop_column('expiration_date_1')

        batch_op.alter_column('family_id', existing_type=sa.Integer(), nullable=False)
