"""
Revision ID: 843bfa914d35
Revises: 02e734fff014
Create Date: 2017-07-12 19:18:40.155472

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '843bfa914d35'
down_revision = '02e734fff014'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('equipment', schema=None) as batch_op:
        batch_op.alter_column('family_id', existing_type=sa.INTEGER(), nullable=False)


def downgrade():
    with op.batch_alter_table('equipment', schema=None) as batch_op:
        batch_op.alter_column('family_id', existing_type=sa.INTEGER(), nullable=True)
