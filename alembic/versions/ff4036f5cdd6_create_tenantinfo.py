"""Create TenantInfo

Revision ID: ff4036f5cdd6
Revises: e8996138f616
Create Date: 2021-03-05 22:34:00.377708

"""

import sqlalchemy as sa
from alembic import op

from asset_tracker import models

# revision identifiers, used by Alembic.
revision = 'ff4036f5cdd6'
down_revision = 'e8996138f616'
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    # noinspection PyUnresolvedReferences
    session = sa.orm.session.Session(bind=connection)

    op.create_table(
        'tenant_info',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Unicode(), nullable=False),
        sa.Column('name', sa.Unicode(), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_tenant_info')),
        sa.UniqueConstraint('tenant_id', name=op.f('uq_tenant_info_tenant_id')),
    )

    with op.batch_alter_table('asset', schema=None) as batch_op:
        batch_op.add_column(sa.Column('tenant_info_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            batch_op.f('fk_asset_tenant_info_id_tenant_info'), 'tenant_info', ['tenant_info_id'], ['id']
        )
        batch_op.drop_column('tenant_name')
        batch_op.alter_column('status_id', existing_type=sa.Integer(), nullable=False)

    with op.batch_alter_table('site', schema=None) as batch_op:
        batch_op.add_column(sa.Column('tenant_info_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            batch_op.f('fk_site_tenant_info_id_tenant_info'), 'tenant_info', ['tenant_info_id'], ['id']
        )
        batch_op.drop_column('tenant_name')

    session.commit()

    tenants_infos = {}

    asset_tenants = [result[0] for result in session.query(models.Asset.tenant_id).group_by(models.Asset.tenant_id)]
    site_tenants = [result[0] for result in session.query(models.Site.tenant_id).group_by(models.Site.tenant_id)]
    tenants_ids = set(asset_tenants + site_tenants)

    for tenant_id in tenants_ids:
        tenant_info = models.TenantInfo(tenant_id=tenant_id, name='Awaiting RTA update')
        session.add(tenant_info)
        tenants_infos[tenant_id] = tenant_info

    for asset in session.query(models.Asset):
        asset.tenant_info = tenants_infos[asset.tenant_id]

    for site in session.query(models.Site):
        site.tenant_info = tenants_infos[site.tenant_id]

    session.commit()

    with op.batch_alter_table('asset', schema=None) as batch_op:
        batch_op.alter_column('tenant_info_id', existing_type=sa.Integer(), nullable=False)

    with op.batch_alter_table('site', schema=None) as batch_op:
        batch_op.alter_column('tenant_info_id', existing_type=sa.Integer(), nullable=False)

    session.commit()


def downgrade():
    with op.batch_alter_table('site', schema=None) as batch_op:
        batch_op.add_column(sa.Column('tenant_name', sa.Unicode(), server_default=sa.text('Fix this'), nullable=False))
        batch_op.drop_constraint(batch_op.f('fk_site_tenant_info_id_tenant_info'), type_='foreignkey')
        batch_op.drop_column('tenant_info_id')

    with op.batch_alter_table('event_status', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('uq_event_status__label_marlink'), type_='unique')
        batch_op.drop_constraint(batch_op.f('uq_event_status__label'), type_='unique')
        batch_op.create_unique_constraint('uq_event_status_label_marlink', ['_label_marlink'])
        batch_op.create_unique_constraint('uq_event_status_label', ['_label'])

    with op.batch_alter_table('asset', schema=None) as batch_op:
        batch_op.add_column(sa.Column('tenant_name', sa.Unicode(), server_default=sa.text('Fix this'), nullable=False))
        batch_op.drop_constraint(batch_op.f('fk_asset_tenant_info_id_tenant_info'), type_='foreignkey')
        batch_op.drop_column('tenant_info_id')
        batch_op.alter_column('status_id', existing_type=sa.Integer(), nullable=True)

    op.drop_table('tenant_info')
