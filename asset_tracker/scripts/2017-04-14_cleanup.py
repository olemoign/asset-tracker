import argparse

from pyramid.paster import bootstrap
from pyramid.scripts.common import parse_vars

from asset_tracker import models
from asset_tracker.constants import CALIBRATION_FREQUENCIES_YEARS
from asset_tracker.views.assets import Assets as AssetView


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('config_uri')
    args, extras = parser.parse_known_args()

    print('Updating stations ...')

    with bootstrap(args.config_uri, options=parse_vars(extras)) as env, env['request'].tm:
        db_session = env['request'].db_session

        in_stock_status = db_session.query(models.EventStatus).filter_by(status_id='stock_parsys').one()

        assets = db_session.query(models.Asset)
        for asset in assets:
            print(f'Asset {asset.id}.')
            # Update calibration_frequency.
            asset.calibration_frequency = CALIBRATION_FREQUENCIES_YEARS['marlink']

            # Add 'in stock' as first event.
            first_event = asset.history('asc').first()
            in_service_event = asset.history('asc') \
                .join(models.Event.status) \
                .filter(models.EventStatus.status_id == 'service') \
                .first()

            if in_service_event is first_event:
                print(f'Adding "in stock" event for asset {asset.id}.')
                # noinspection PyArgumentList
                in_stock_event = models.Event(
                    creator_id='59EcBjjl',
                    creator_alias='TISON Sylvain',
                    date=in_service_event.date,
                    status=in_stock_status,
                )
                asset.add_event(in_stock_event)
                db_session.add(in_stock_event)

            # Update calibration_next.
            AssetView.update_calibration_next(asset)

            print()

    print('Done.')


if __name__ == '__main__':
    main()
