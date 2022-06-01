"""19/12/2019: transfer glucose meter consumable expiration date information on the new consumables table."""
import argparse

from pyramid.paster import bootstrap
from pyramid.scripts.common import parse_vars
from sqlalchemy import or_

from asset_tracker import models

LANCETS_ID = 'GZQ2bAmW'
TEST_STRIPS_ID = '9oL6q5O5'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('config_uri')
    args, extras = parser.parse_known_args()

    print('Migrating equipments expiration dates.')

    options = parse_vars(extras)
    with bootstrap(args.config_uri, options=options) as env, env['request'].tm:
        db_session = env['request'].db_session

        lancets = db_session.query(models.ConsumableFamily).filter_by(family_id=LANCETS_ID).first()
        test_strips = db_session.query(models.ConsumableFamily).filter_by(family_id=TEST_STRIPS_ID).first()

        equipments_to_migrate = db_session.query(models.Equipment) \
            .filter(or_(
                models.Equipment.expiration_date_1.isnot(None),
                models.Equipment.expiration_date_2.isnot(None),
            ))

        for equipment in equipments_to_migrate:
            if equipment.expiration_date_1:
                db_session.add(models.Consumable(
                    family=lancets,
                    equipment_id=equipment.id,
                    expiration_date=equipment.expiration_date_1,
                ))
                print(f'Created lancets consumable for equipment {equipment.id}.')

            if equipment.expiration_date_2:
                db_session.add(models.Consumable(
                    family=test_strips,
                    equipment_id=equipment.id,
                    expiration_date=equipment.expiration_date_2,
                ))
                print(f'Created test strips consumable for equipment {equipment.id}.')

    print('Done.')


if __name__ == '__main__':
    main()
