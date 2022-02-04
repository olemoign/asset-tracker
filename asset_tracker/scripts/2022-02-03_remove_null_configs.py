import argparse
import json

from depot.manager import DepotManager
from pyramid.paster import bootstrap
from pyramid.scripts.common import parse_vars

from asset_tracker import models


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('config_uri')
    args, extras = parser.parse_known_args()

    print('Removing null configs...')

    options = parse_vars(extras)
    with bootstrap(args.config_uri, options=options) as env, env['request'].tm:
        db_session = env['request'].db_session
        depot = DepotManager.get()

        events = db_session.query(models.Event) \
            .join(models.Event.status) \
            .filter(models.EventStatus.status_id == 'config_update')
        for event in events:
            try:
                config_file = depot.get(event.extra_json['config'])
                config = config_file.read().decode('utf-8')
            except (json.JSONDecodeError, OSError, TypeError, ValueError) as error:
                print(f'{event.id}: {error}')
                config = None

            if config == 'null':
                print(f'{event.id}: "null" file, deleting.')
                depot.delete(event.extra_json['config'])
                db_session.delete(event)

    print('Done.')


if __name__ == '__main__':
    main()
