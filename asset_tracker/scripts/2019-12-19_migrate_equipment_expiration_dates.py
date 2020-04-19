"""19/12/2019: transfer glucose meter consumable expiration date information on the new consumables table."""
import argparse

from pyramid.paster import bootstrap
from pyramid.scripts.common import parse_vars
from sqlalchemy import or_

from asset_tracker.models import Consumable, ConsumableFamily, Equipment


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('config_uri')
    args, extras = parser.parse_known_args()

    print('Migrate equipment expiration date data.')

    options = parse_vars(extras)
    with bootstrap(args.config_uri, options=options) as env, env['request'].tm:
        db_session = env['request'].db_session

        lancets = db_session.query(ConsumableFamily).filter_by(family_id='GZQ2bAmW').first()
        test_strips = db_session.query(ConsumableFamily).filter_by(family_id='6piDwmZt').first()

        equipments_to_migrate = db_session.query(Equipment) \
            .filter(or_(Equipment.expiration_date_1, Equipment.expiration_date_2)).all()

        for equipment in equipments_to_migrate:
            if equipment.expiration_date_1:
                db_session.add(Consumable(
                    family=lancets,
                    equipment_id=equipment.id,
                    expiration_date=equipment.expiration_date_1,
                ))
                print(f'Created lancets consumable for equipment {equipment.id}.')

            if equipment.expiration_date_2:
                db_session.add(Consumable(
                    family=test_strips,
                    equipment_id=equipment.id,
                    expiration_date=equipment.expiration_date_2,
                ))
                print(f'Created test strips consumable for equipment {equipment.id}.')

    print('Done.')


if __name__ == '__main__':
    main()
