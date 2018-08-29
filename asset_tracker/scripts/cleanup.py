import argparse

from dateutil.relativedelta import relativedelta
from pyramid.paster import bootstrap
from pyramid.scripts.common import parse_vars

from asset_tracker import models


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('config_uri')
    args, extras = parser.parse_known_args()

    print('Updating stations ...')

    with bootstrap(args.config_uri, options=parse_vars(extras)) as env, env['request'].tm:
        db_session = env['request'].db_session

        in_stock_status = db_session.query(models.EventStatus).filter_by(status_id='stock_parsys').first()

        assets = db_session.query(models.Asset)
        for asset in assets:
            print('Asset {}.'.format(asset.id))
            # Update calibration_frequency
            asset.calibration_frequency = 3

            # Add 'in stock' as first event
            # noinspection PyProtectedMember
            first_event = asset._history.order_by(models.Event.date).first()
            # noinspection PyProtectedMember
            in_service_event = asset._history.join(models.EventStatus) \
                .filter(models.EventStatus.status_id == 'service').order_by(models.Event.date).first()

            if in_service_event is first_event:
                print('Adding "in stock" event.'.format(asset.id))
                # noinspection PyArgumentList
                in_stock_event = models.Event(date=in_service_event.date, creator_id='59EcBjjl',
                                              creator_alias='TISON Sylvain', status=in_stock_status)
                # noinspection PyProtectedMember
                asset._history.append(in_stock_event)
                db_session.add(in_stock_event)

            # Update status
            asset.status = asset.history('desc').first().status

            # Update calibration_next
            if asset.calibration_last:
                asset.calibration_next = asset.calibration_last + relativedelta(years=asset.calibration_frequency)

            print()

    print('Done.')


if __name__ == '__main__':
    main()
