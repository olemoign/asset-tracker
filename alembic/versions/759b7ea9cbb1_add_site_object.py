"""add Site object

Revision ID: 759b7ea9cbb1
Revises: f22d6bf9b6b6
Create Date: 2017-09-07 19:54:29.102511

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '759b7ea9cbb1'
down_revision = 'f22d6bf9b6b6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('site',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('created_at', sa.DateTime(), nullable=False),
                    sa.Column('tenant_id', sa.Unicode(), nullable=False),
                    sa.Column('type', sa.Unicode(), nullable=False),
                    sa.Column('contact', sa.Unicode(), nullable=True),
                    sa.Column('phone', sa.Unicode(), nullable=True),
                    sa.Column('email', sa.Unicode(), nullable=True),
                    sa.PrimaryKeyConstraint('id', name=op.f('pk_site')),
                    sa.UniqueConstraint('type', name=op.f('uq_site_type'))
                    )
    with op.batch_alter_table('asset', schema=None) as batch_op:
        batch_op.add_column(sa.Column('site_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(batch_op.f('fk_asset_site_id_site'), 'site', ['site_id'], ['id'])
        batch_op.drop_column('site')


def downgrade():
    with op.batch_alter_table('asset', schema=None) as batch_op:
        batch_op.add_column(sa.Column('site', sa.VARCHAR(), nullable=True))
        batch_op.drop_constraint(batch_op.f('fk_asset_site_id_site'), type_='foreignkey')
        batch_op.drop_column('site_id')

    op.drop_table('site')
