import argparse

import transaction
from pyramid.paster import bootstrap
from pyramid.scripts.common import parse_vars

from asset_tracker import models


parser = argparse.ArgumentParser()
parser.add_argument('config_uri')
args, extras = parser.parse_known_args()

print('Deleting unnecessary calibrations ...')

with bootstrap(args.config_uri, options=parse_vars(extras)) as env:
    with transaction.manager:
        db_session = env['request'].db_session

        assets = db_session.query(models.Asset)
        for asset in assets:
            # noinspection PyProtectedMember
            calibration = asset._history.join(models.EventStatus).filter(models.EventStatus.status_id == 'calibration') \
                .order_by(models.Event.date).first()
            # noinspection PyProtectedMember
            service = asset._history.join(models.EventStatus).filter(models.EventStatus.status_id == 'service') \
                .order_by(models.Event.date).first()

            if calibration and service and calibration.date == service.date:
                print('Deleting calibration ({}) for asset {}.'.format(calibration.date, asset.id))
                db_session.delete(calibration)

print('Done.')
