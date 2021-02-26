"""Fix equipments families

Revision ID: 52f92ee869a0
Revises: e8996138f616
Create Date: 2021-02-26 18:23:11.762408

"""

from alembic import op
import sqlalchemy as sa

from asset_tracker import models


# revision identifiers, used by Alembic.
revision = '52f92ee869a0'
down_revision = 'e8996138f616'
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    # noinspection PyUnresolvedReferences
    session = sa.orm.session.Session(bind=connection)

    good_family = session.query(models.EquipmentFamily).filter_by(family_id='c494zUZ0').first()
    biosys_list = session.query(models.Equipment).join(models.EquipmentFamily) \
        .filter(models.EquipmentFamily.family_id == 'AWmOOZin')
    for biosys in biosys_list:
        biosys.family = good_family

    good_family = session.query(models.EquipmentFamily).filter_by(family_id='CJR99XSW').first()
    telecardia_list = session.query(models.Equipment).join(models.EquipmentFamily) \
        .filter(models.EquipmentFamily.family_id == 'psqeAtt1')
    for telecardia in telecardia_list:
        telecardia.family = good_family

    good_family = session.query(models.EquipmentFamily).filter_by(family_id='jbVmQunF').first()
    fora_ir21_list = session.query(models.Equipment).join(models.EquipmentFamily) \
        .filter(models.EquipmentFamily.family_id == 'hC5QzQL1')
    for fora_ir21 in fora_ir21_list:
        fora_ir21.family = good_family

    session.commit()


def downgrade():
    pass
