import argparse
from csv import reader
from datetime import date

import transaction
from pyramid.paster import get_appsettings, setup_logging
from pyramid.scripts.common import parse_vars

from asset_tracker.models import Asset, Equipment, Event, get_engine, get_session_factory, get_tm_session


parser = argparse.ArgumentParser()
parser.add_argument('config_uri')
args, extras = parser.parse_known_args()

setup_logging(args.config_uri)
settings = get_appsettings(args.config_uri, options=parse_vars(extras))

engine = get_engine(settings)
db_session_factory = get_session_factory(engine)

with transaction.manager:
    db_session = get_tm_session(db_session_factory, transaction.manager)

    with open('/Users/olemoign/Downloads/asset_tracker/cma_cgm.csv') as csv_file:
        csv_reader = reader(csv_file, delimiter=';')
        headers = next(csv_reader)

        for row in csv_reader:
            fleet, _, _, _, vessel, kit_id, base_id, telecardia_id, _ = row
            if kit_id and base_id and telecardia_id:
                print(vessel)
                # noinspection PyArgumentList
                kit = Asset(asset_id=kit_id, tenant_id='JWUdWAlq', customer_name=fleet, site=vessel)

                base = Equipment(family_id=9, serial_number=base_id)
                telecardia = Equipment(family_id=2, serial_number=telecardia_id)
                kit.equipments.append(base)
                kit.equipments.append(telecardia)

                production = Event(date=date(2014, 1, 1), creator_id='X9A39F0g', creator_alias='Sylvain TISON',
                                   status='produced')
                activation = Event(date=date(2014, 1, 1), creator_id='X9A39F0g', creator_alias='Sylvain TISON',
                                   status='service')
                kit.history.append(production)
                kit.history.append(activation)

                db_session.add_all([kit, base, telecardia, production, activation])
