"""Add software_version

Revision ID: cf8b307316af
Revises: e48836ce2279
Create Date: 2016-06-22 16:31:26.849171

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'cf8b307316af'
down_revision = 'e48836ce2279'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('asset', sa.Column('software_version', sa.Unicode(), nullable=True))


def downgrade():
    op.drop_column('asset', 'software_version')
