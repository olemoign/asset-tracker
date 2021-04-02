"""Migrate event status

Revision ID: 67ca562dfc8c
Revises: 6715e132d14a
Create Date: 2021-03-04 16:46:08.464391

"""

import sqlalchemy as sa
from alembic import op

from asset_tracker import models

# revision identifiers, used by Alembic.
revision = '67ca562dfc8c'
down_revision = '6715e132d14a'
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    # noinspection PyUnresolvedReferences
    session = sa.orm.session.Session(bind=connection)

    incident = session.query(models.EventStatus).filter_by(status_id='incident').first()
    if incident:
        incident.status_id = 'replacement_failure'

    replacement = session.query(models.EventStatus).filter_by(status_id='replacement').first()
    if replacement:
        replacement.status_id = 'replacement_calibration'

    session.commit()


def downgrade():
    connection = op.get_bind()
    # noinspection PyUnresolvedReferences
    session = sa.orm.session.Session(bind=connection)

    incident = session.query(models.EventStatus).filter_by(status_id='replacement_failure').first()
    incident.status_id = 'incident'

    replacement = session.query(models.EventStatus).filter_by(status_id='replacement_calibration').first()
    replacement.status_id = 'replacement'

    session.commit()
