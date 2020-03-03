"""Add asset.mac_wifi/ethernet

Revision ID: 5d889b6e1931
Revises: 80c54335e8c0
Create Date: 2020-03-03 16:52:37.570792

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '5d889b6e1931'
down_revision = '80c54335e8c0'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('asset', schema=None) as batch_op:
        batch_op.add_column(sa.Column('mac_ethernet', sa.Unicode(), nullable=True))
        batch_op.add_column(sa.Column('mac_wifi', sa.Unicode(), nullable=True))

    with op.batch_alter_table('event_status', schema=None) as batch_op:
        batch_op.alter_column('status_type', existing_type=sa.Unicode(), nullable=False)


def downgrade():
    with op.batch_alter_table('event_status', schema=None) as batch_op:
        batch_op.alter_column('status_type', existing_type=sa.Unicode(), nullable=True)

    with op.batch_alter_table('asset', schema=None) as batch_op:
        batch_op.drop_column('mac_wifi')
        batch_op.drop_column('mac_ethernet')
