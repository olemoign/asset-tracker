"""24/07/2018: Export sites to set them in the Cloud."""
import argparse
import csv

from pyramid.paster import bootstrap
from pyramid.scripts.common import parse_vars

from asset_tracker import models


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('config_file')
    parser.add_argument('output', nargs='?', default='sites.csv')
    args, extras = parser.parse_known_args()

    print('Exporting sites.')

    with bootstrap(args.config_file, options=parse_vars(extras)) as env, env['request'].tm, \
            open(args.output, 'w') as csv_file:
        db_session = env['request'].db_session
        writer = csv.writer(csv_file)

        sites = db_session.query(models.Site).order_by(models.Site.tenant_id, models.Site.name)
        count = sites.count()
        for site in sites:
            writer.writerow([site.tenant_id, site.name, site.site_id])

    print(f'Exported {count} sites.')


if __name__ == '__main__':
    main()
