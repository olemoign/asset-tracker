"""Add site_id

Revision ID: 70292af6fd9e
Revises: 72daf9faa92b
Create Date: 2018-07-16 12:05:18.423951

"""

import sqlalchemy as sa
from alembic import op
from parsys_utilities import random_id
from sqlalchemy.orm import declarative_base, Session

# revision identifiers, used by Alembic.
revision = '70292af6fd9e'
down_revision = '72daf9faa92b'
branch_labels = None
depends_on = None

Model = declarative_base()


class Site(Model):
    __tablename__ = 'site'
    id = sa.Column(sa.Integer, primary_key=True)
    site_id = sa.Column(sa.String, nullable=False, unique=True)


def upgrade():
    connection = op.get_bind()
    session = Session(bind=connection)

    with op.batch_alter_table('site', schema=None) as batch_op:
        batch_op.add_column(sa.Column('site_id', sa.Unicode()))
        batch_op.create_unique_constraint(batch_op.f('uq_site_site_id'), ['site_id'])
    session.commit()

    for site in session.query(Site).all():
        site.site_id = random_id()
    session.commit()

    with op.batch_alter_table('site', schema=None) as batch_op:
        batch_op.alter_column('site_id', existing_type=sa.Unicode(), nullable=False)
    session.commit()


def downgrade():
    with op.batch_alter_table('site', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('uq_site_site_id'), type_='unique')
        batch_op.drop_column('site_id')
