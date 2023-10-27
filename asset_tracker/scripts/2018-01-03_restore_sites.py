"""03/01/2018: Restore sites data that was lost during 2.7 migration."""
import argparse
import csv

from pyramid.paster import bootstrap
from pyramid.scripts.common import parse_vars

from asset_tracker import models


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('config_file')
    parser.add_argument('csv_file')
    args, extras = parser.parse_known_args()

    print('Restoring sites data.')

    options = parse_vars(extras)
    with bootstrap(args.config_file, options=options) as env, env['request'].tm, open(args.csv_file) as csv_file:
        db_session = env['request'].db_session
        csv_reader = csv.reader(csv_file, delimiter=';')

        for asset_id, site_name in csv_reader:
            asset = db_session.query(models.Asset).filter_by(asset_id=asset_id).first()

            if not asset:
                print(f'Asset {asset_id} not found.')
                continue

            if site_name:
                site = db_session.query(models.Site).filter_by(name=site_name).first()

                if not site:
                    site = models.Site(tenant_id=asset.tenant_id, name=site_name)

                    if site_name.startswith('CMA CGM') or site_name.startswith('APL'):
                        site.site_type = 'Ship'
                    else:
                        site.site_type = 'Company'

                    db_session.add(site)

                asset.site = site
                print(f'Site {site_name} added for asset {asset_id}.')

            else:
                print(f'No site for asset {asset_id}.')

    print('Done.')


if __name__ == '__main__':
    main()
