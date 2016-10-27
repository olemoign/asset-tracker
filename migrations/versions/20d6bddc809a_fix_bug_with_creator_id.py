"""Fix bug with creator_id

Revision ID: 20d6bddc809a
Revises: cf8b307316af
Create Date: 2016-06-27 17:44:24.595570

"""

# revision identifiers, used by Alembic.
revision = '20d6bddc809a'
down_revision = 'cf8b307316af'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    with op.batch_alter_table('event') as batch_op:
        batch_op.alter_column('creator_id', existing_type=sa.Integer(), type_=sa.Unicode())


def downgrade():
    with op.batch_alter_table('event') as batch_op:
        batch_op.alter_column('creator_id', existing_type=sa.Unicode(), type_=sa.Integer())
