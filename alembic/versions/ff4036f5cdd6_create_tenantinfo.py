"""Create TenantInfo

Revision ID: ff4036f5cdd6
Revises: e8996138f616
Create Date: 2021-03-05 22:34:00.377708

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.orm import declarative_base, relationship, Session

# revision identifiers, used by Alembic.
revision = 'ff4036f5cdd6'
down_revision = 'e8996138f616'
branch_labels = None
depends_on = None

Model = declarative_base()


class Asset(Model):
    __tablename__ = 'asset'
    id = sa.Column(sa.Integer, primary_key=True)
    tenant_id = sa.Column(sa.String, nullable=False)
    tenant_info_id = sa.Column(sa.Integer, sa.ForeignKey('tenant_info.id'), nullable=False)
    tenant_info = relationship('TenantInfo', foreign_keys=tenant_info_id, backref='assets', uselist=False)


class Site(Model):
    __tablename__ = 'site'
    id = sa.Column(sa.Integer, primary_key=True)
    tenant_id = sa.Column(sa.String, nullable=False)
    tenant_info_id = sa.Column(sa.Integer, sa.ForeignKey('tenant_info.id'), nullable=False)
    tenant_info = relationship('TenantInfo', foreign_keys=tenant_info_id, backref='sites', uselist=False)


class TenantInfo(Model):
    __tablename__ = 'tenant_info'
    id = sa.Column(sa.Integer, primary_key=True)
    tenant_id = sa.Column(sa.String, nullable=False, unique=True)
    name = sa.Column(sa.String, nullable=False)


def upgrade():
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

    connection = op.get_bind()
    db_session = Session(bind=connection)
    db_session.commit()

    tenants_infos = {}

    asset_tenants = [result[0] for result in db_session.query(Asset.tenant_id).group_by(Asset.tenant_id)]
    site_tenants = [result[0] for result in db_session.query(Site.tenant_id).group_by(Site.tenant_id)]
    tenants_ids = set(asset_tenants + site_tenants)

    for tenant_id in tenants_ids:
        tenant_info = TenantInfo(tenant_id=tenant_id, name='Awaiting RTA update')
        db_session.add(tenant_info)
        tenants_infos[tenant_id] = tenant_info

    for asset in db_session.query(Asset):
        asset.tenant_info = tenants_infos[asset.tenant_id]

    for site in db_session.query(Site):
        site.tenant_info = tenants_infos[site.tenant_id]

    db_session.commit()

    with op.batch_alter_table('asset', schema=None) as batch_op:
        batch_op.alter_column('tenant_info_id', existing_type=sa.Integer(), nullable=False)

    with op.batch_alter_table('site', schema=None) as batch_op:
        batch_op.alter_column('tenant_info_id', existing_type=sa.Integer(), nullable=False)

    db_session.commit()


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
