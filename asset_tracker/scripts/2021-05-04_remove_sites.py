"""04/05/2021: remove sites from decommissioned assets."""

import argparse
import csv
from datetime import datetime

from pyramid.paster import bootstrap
from pyramid.scripts.common import parse_vars

from asset_tracker import models


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('config_file')
    parser.add_argument('csv_file')
    args, extras = parser.parse_known_args()

    print('Removing sites from decommissioned assets.')

    options = parse_vars(extras)
    with bootstrap(args.config_file, options=options) as env, env['request'].tm, open(args.csv_file) as csv_file:
        db_session = env['request'].db_session
        csv_reader = csv.reader(csv_file, delimiter=';')

        site_change = db_session.query(models.EventStatus).filter_by(status_id='site_change').one()

        for row in csv_reader:
            (
                asset_id,
                site_entry,
                site_exit,
                production,
                activation,
                calibration_last,
                calibration_next,
                warranty_end,
                site_name,
            ) = row

            asset = db_session.query(models.Asset) \
                .join(models.Asset.status) \
                .outerjoin(models.Asset.site) \
                .filter(models.Asset.asset_id == asset_id) \
                .one()

            if not asset.site:
                continue

            event = models.Event(
                creator_id='MFjUDRnl',
                creator_alias='Olivier Le Moign',
                date=datetime.strptime(site_exit, '%d/%m/%Y').date(),
                status=site_change,
            )
            asset.add_event(event)
            db_session.add(event)

            asset.site_id = None

    print('Done.')


if __name__ == '__main__':
    main()
