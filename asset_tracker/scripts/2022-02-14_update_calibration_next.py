import argparse

from dateutil.relativedelta import relativedelta
from pyramid.paster import bootstrap
from pyramid.scripts.common import parse_vars

from asset_tracker import models
from asset_tracker.constants import CALIBRATION_FREQUENCIES_YEARS


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('config_file')
    args, extras = parser.parse_known_args()

    print('Updating calibration_next...')

    options = parse_vars(extras)
    with bootstrap(args.config_file, options=options) as env, env['request'].tm:
        db_session = env['request'].db_session

        print('Consumable cases')
        for case in db_session.query(models.Asset).filter_by(asset_type='consumables_case'):
            case.calibration_next = None
            print(case.asset_id)
            print(case.calibration_next)
        print()

        print('Decommissioned')
        assets = db_session.query(models.Asset) \
            .join(models.Asset.status) \
            .filter(models.EventStatus.status_id == 'decommissioned')
        for asset in assets:
            asset.calibration_next = None
            print(asset.asset_id)
            print(asset.calibration_next)
        print()

        print('Stations')
        delta = relativedelta(years=CALIBRATION_FREQUENCIES_YEARS['marlink'])
        assets = db_session.query(models.Asset) \
            .join(models.Asset.status) \
            .filter(
                models.Asset.asset_type != 'consumables_case',
                models.EventStatus.status_id != 'decommissioned',
                ~models.Asset.asset_id.ilike('STHT%'),
            )
        for asset in assets:
            asset.calibration_frequency = 4
            if asset.calibration_last:
                print(asset.asset_id)
                print(asset.calibration_next)
                asset.calibration_next = asset.calibration_last + delta
                print(asset.calibration_next)

    print('Done.')


if __name__ == '__main__':
    main()
