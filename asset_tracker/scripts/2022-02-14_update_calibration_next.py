import argparse

from dateutil.relativedelta import relativedelta
from pyramid.paster import bootstrap
from pyramid.scripts.common import parse_vars

from asset_tracker import models
from asset_tracker.constants import CALIBRATION_FREQUENCIES_YEARS


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('config_uri')
    args, extras = parser.parse_known_args()

    print('Updating calibration_next...')

    options = parse_vars(extras)
    with bootstrap(args.config_uri, options=options) as env, env['request'].tm:
        db_session = env['request'].db_session

        for case in db_session.query(models.Asset).filter_by(asset_type='consumables_case'):
            case.calibration_next = None
            print(case.asset_id)
            print(case.calibration_next)

        delta = relativedelta(years=CALIBRATION_FREQUENCIES_YEARS['marlink'])
        assets = db_session.query(models.Asset) \
            .filter(
                models.Asset.asset_type != 'consumables_case',
                ~models.Asset.asset_id.ilike('STHT%'),
            )
        for asset in assets:
            if asset.calibration_last:
                print(asset.asset_id)
                print(asset.calibration_next)
                asset.calibration_next = asset.calibration_last + delta
                print(asset.calibration_next)

    print('Done.')


if __name__ == '__main__':
    main()
