import argparse
import csv
import sys
from datetime import datetime, timedelta

import transaction
from dateutil.relativedelta import relativedelta
from pyramid.paster import bootstrap
from pyramid.scripts.common import parse_vars

from asset_tracker.constants import CALIBRATION_FREQUENCIES_YEARS
from asset_tracker.models import Asset, Equipment, EquipmentFamily, Event, EventStatus


parser = argparse.ArgumentParser()
parser.add_argument('config_uri')
parser.add_argument('csv_file')
parser.add_argument('tenant_id')
parser.add_argument('creator_id')
parser.add_argument('creator_alias')
args, extras = parser.parse_known_args()

with bootstrap(args.config_uri, options=parse_vars(extras)) as env:
    with transaction.manager:
        db_session = env['request'].db_session

        with open(args.csv_file) as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=';')

            family_base = db_session.query(EquipmentFamily).filter_by(family_id='j7tJ1y4A').first()
            family_telecardia = db_session.query(EquipmentFamily).filter_by(family_id='psqeAtt1').first()

            calibration_status = db_session.query(EventStatus).filter_by(status_id='calibration').first()
            activation_status = db_session.query(EventStatus).filter_by(status_id='service').first()

            for row_number, row in enumerate(csv_reader):
                vessel, kit_id, base_id, telecardia_id, calibration_date = row
                if not vessel or not kit_id or not base_id or not telecardia_id or not calibration_date:
                    print('Row {} is invalid.'.format(row_number))
                    db_session.rollback()
                    sys.exit()

                print('Added asset for vessel {}'.format(vessel))
                # noinspection PyArgumentList
                kit = Asset(asset_id=kit_id, tenant_id=args.tenant_id, asset_type='telecardia', customer_name='CMA CGM',
                            site=vessel)

                base = Equipment(family=family_base, serial_number=base_id)
                telecardia = Equipment(family=family_telecardia, serial_number=telecardia_id)
                kit.equipments.append(base)
                kit.equipments.append(telecardia)

                calibration_date = datetime.strptime(calibration_date, '%d/%m/%y')
                # noinspection PyArgumentList
                calibration = Event(date=calibration_date, creator_id=args.creator_id, creator_alias=args.creator_alias,
                                    status=calibration_status)
                # noinspection PyArgumentList
                activation = Event(date=calibration_date + timedelta(hours=1), creator_id=args.creator_id,
                                   creator_alias=args.creator_alias, status=activation_status)
                # noinspection PyProtectedMember
                kit._history.append(calibration)
                # noinspection PyProtectedMember
                kit._history.append(activation)

                kit.status = activation_status
                kit.calibration_next = calibration_date + relativedelta(years=CALIBRATION_FREQUENCIES_YEARS['maritime'])

                db_session.add_all([kit, base, telecardia, calibration, activation])
