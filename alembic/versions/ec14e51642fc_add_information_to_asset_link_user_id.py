"""add information to Asset: link & user_id

Revision ID: ec14e51642fc
Revises: f22d6bf9b6b6
Create Date: 2017-09-11 17:17:54.345418

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ec14e51642fc'
down_revision = 'f22d6bf9b6b6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('asset', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_linked', sa.Boolean(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('user_id', sa.Unicode(), nullable=True))


def downgrade():
    with op.batch_alter_table('asset', schema=None) as batch_op:
        batch_op.drop_column('user_id')
        batch_op.drop_column('is_linked')
