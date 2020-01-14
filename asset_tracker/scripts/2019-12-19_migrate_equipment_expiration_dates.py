"""19/12/2019: transfer Glucose meter consumable expiration date information on the new consumable table."""
import argparse

from pyramid.paster import bootstrap
from pyramid.scripts.common import parse_vars
from sqlalchemy import or_

from asset_tracker.models import Equipment, Consumable


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('config_uri')
    args, extras = parser.parse_known_args()

    print('Migrate equipment expiration date data.')

    options = parse_vars(extras)
    with bootstrap(args.config_uri, options=options) as env, env['request'].tm:
        db_session = env['request'].db_session

        equipments_to_migrate = db_session.query(Equipment).filter(
            or_(Equipment.expiration_date_1, Equipment.expiration_date_2)
        ).all()

        for equipment in equipments_to_migrate:
            if equipment.expiration_date_1:
                db_session.add(Consumable(
                    family_id=1,
                    equipment_id=equipment.id,
                    expiration_date=equipment.expiration_date_1,
                ))
                print(f'Created lancets consumable for equipment {equipment.id}.')
            if equipment.expiration_date_2:
                db_session.add(Consumable(
                    family_id=2,
                    equipment_id=equipment.id,
                    expiration_date=equipment.expiration_date_2,
                ))
                print(f'Created test strips consumable for equipment {equipment.id}.')

    print('Done.')


if __name__ == '__main__':
    main()
