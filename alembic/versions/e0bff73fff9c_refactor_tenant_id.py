"""Refactor tenant_id

Revision ID: e0bff73fff9c
Revises: ff4036f5cdd6
Create Date: 2021-05-04 16:16:10.724909

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.orm import Session

from asset_tracker import models

# revision identifiers, used by Alembic.
revision = 'e0bff73fff9c'
down_revision = 'ff4036f5cdd6'
branch_labels = None
depends_on = None


def upgrade():
    op.rename_table('tenant_info', 'tenant')

    with op.batch_alter_table('asset', schema=None) as batch_op:
        batch_op.drop_column('tenant_id')
        batch_op.alter_column('tenant_info_id', new_column_name='tenant_id')

    with op.batch_alter_table('site', schema=None) as batch_op:
        batch_op.drop_column('tenant_id')
        batch_op.alter_column('tenant_info_id', new_column_name='tenant_id')

    if op.get_bind().engine.name == 'sqlite':
        return

    op.execute('ALTER INDEX pk_tenant_info RENAME TO pk_tenant')
    op.execute('ALTER TABLE asset RENAME CONSTRAINT fk_asset_tenant_info_id_tenant_info TO fk_asset_tenant_id_tenant')
    op.execute('ALTER TABLE site RENAME CONSTRAINT fk_site_tenant_info_id_tenant_info TO fk_site_tenant_id_tenant')


def downgrade():
    connection = op.get_bind()
    session = Session(bind=connection)

    op.rename_table('tenant', 'tenant_info')

    with op.batch_alter_table('asset', schema=None) as batch_op:
        batch_op.alter_column('tenant_id', new_column_name='tenant_info_id')
        batch_op.add_column(sa.Column('tenant_id', sa.Unicode(), nullable=True))

    with op.batch_alter_table('site', schema=None) as batch_op:
        batch_op.alter_column('tenant_id', new_column_name='tenant_info_id')
        batch_op.add_column(sa.Column('tenant_id', sa.Unicode(), nullable=True))

    session.commit()

    for asset in session.query(models.Asset).join(models.Asset.tenant_info):
        asset.tenant_id = asset.tenant_info.tenant_id

    for site in session.query(models.Site).join(models.Site.tenant_info):
        site.tenant_id = site.tenant_info.tenant_id

    session.commit()

    with op.batch_alter_table('asset', schema=None) as batch_op:
        batch_op.alter_column('tenant_id', existing_type=sa.Unicode(), nullable=False)

    with op.batch_alter_table('site', schema=None) as batch_op:
        batch_op.alter_column('tenant_id', existing_type=sa.Unicode(), nullable=False)

    session.commit()

    if op.get_bind().engine.name == 'sqlite':
        return

    op.execute('ALTER INDEX pk_tenant RENAME TO pk_tenant_info')
    op.execute('ALTER TABLE asset RENAME CONSTRAINT fk_asset_tenant_id_tenant TO fk_asset_tenant_info_id_tenant_info')
    op.execute('ALTER TABLE site RENAME CONSTRAINT fk_site_tenant_id_tenant TO fk_site_tenant_info_id_tenant_info')
