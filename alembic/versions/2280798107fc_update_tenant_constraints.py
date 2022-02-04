"""Update tenant constraints

Revision ID: 2280798107fc
Revises: e0bff73fff9c
Create Date: 2022-02-03 18:28:06.128551

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = '2280798107fc'
down_revision = 'e0bff73fff9c'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('tenant', schema=None) as batch_op:
        batch_op.drop_constraint('uq_tenant_info_tenant_id', type_='unique')
        batch_op.create_unique_constraint(batch_op.f('uq_tenant_tenant_id'), ['tenant_id'])


def downgrade():
    with op.batch_alter_table('tenant', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('uq_tenant_tenant_id'), type_='unique')
        batch_op.create_unique_constraint('uq_tenant_info_tenant_id', ['tenant_id'])
