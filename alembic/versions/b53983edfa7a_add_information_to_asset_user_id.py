"""add information to Asset: user_id
RTA will populate this field when create/edit station.
This field allow to get information about Asset from consultation.

Revision ID: b53983edfa7a
Revises: f22d6bf9b6b6
Create Date: 2017-09-19 12:26:13.867439

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'b53983edfa7a'
down_revision = 'f22d6bf9b6b6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('asset', schema=None) as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.Unicode(), nullable=True))


def downgrade():
    with op.batch_alter_table('asset', schema=None) as batch_op:
        batch_op.drop_column('user_id')
