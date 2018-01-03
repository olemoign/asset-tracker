"""03/01/2018: Restore sites data that was lost during 2.7 migration."""
import argparse
import csv

import transaction
from pyramid.paster import bootstrap
from pyramid.scripts.common import parse_vars

from asset_tracker.models import Asset, Site


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('config_uri')
    parser.add_argument('csv_file')
    args, extras = parser.parse_known_args()

    print('Restoring sites data.')

    with bootstrap(args.config_uri, options=parse_vars(extras)) as env, transaction.manager, \
            open(args.csv_file) as csv_file:
        db_session = env['request'].db_session
        csv_reader = csv.reader(csv_file, delimiter=';')

        for asset_id, site_name in csv_reader:
            asset = db_session.query(Asset).filter_by(asset_id=asset_id).first()

            if not asset:
                print('Asset {} not found.'.format(asset_id))
                continue

            if site_name:
                site = db_session.query(Site).filter_by(name=site_name).first()

                if not site:
                    site = Site(tenant_id=asset.tenant_id, name=site_name)

                    if site_name.startswith('CMA CGM') or site_name.startswith('APL'):
                        site.site_type = 'Ship'
                    else:
                        site.site_type = 'Company'

                    db_session.add(site)
                    
                asset.site = site
                print('Site {} added for asset {}.'.format(site_name, asset_id))

            else:
                print('No site for asset {}.'.format(asset_id))

    print('Done.')


if __name__ == '__main__':
    main()
