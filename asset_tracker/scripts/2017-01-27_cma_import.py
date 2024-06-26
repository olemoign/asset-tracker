import argparse
import csv
import sys
from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta
from pyramid.paster import bootstrap
from pyramid.scripts.common import parse_vars

from asset_tracker import models
from asset_tracker.constants import CALIBRATION_FREQUENCIES_YEARS


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('config_file')
    parser.add_argument('csv_file')
    parser.add_argument('tenant_id')
    parser.add_argument('creator_id')
    parser.add_argument('creator_alias')
    args, extras = parser.parse_known_args()

    options = parse_vars(extras)
    with bootstrap(args.config_file, options=options) as env, env['request'].tm, open(args.csv_file) as csv_file:
        db_session = env['request'].db_session
        csv_reader = csv.reader(csv_file, delimiter=';')

        family_base = db_session.query(models.EquipmentFamily).filter_by(family_id='j7tJ1y4A').first()
        family_telecardia = db_session.query(models.EquipmentFamily).filter_by(family_id='psqeAtt1').first()

        calibration_status = db_session.query(models.EventStatus).filter_by(status_id='calibration').one()
        activation_status = db_session.query(models.EventStatus).filter_by(status_id='service').one()

        for row_number, row in enumerate(csv_reader):
            vessel, kit_id, base_id, telecardia_id, calibration_date = row
            if not vessel or not kit_id or not base_id or not telecardia_id or not calibration_date:
                print(f'Row {row_number} is invalid.')
                db_session.rollback()
                sys.exit()

            print(f'Added asset for vessel {vessel}')
            kit = models.Asset(
                asset_id=kit_id,
                tenant_id=args.tenant_id,
                asset_type='telecardia',
                customer_name='CMA CGM',
                site=vessel,
            )

            base = models.Equipment(family=family_base, serial_number=base_id)
            telecardia = models.Equipment(family=family_telecardia, serial_number=telecardia_id)
            kit.equipments.append(base)
            kit.equipments.append(telecardia)

            calibration_date = datetime.strptime(calibration_date, '%d/%m/%y').date()
            calibration = models.Event(
                date=calibration_date,
                creator_id=args.creator_id,
                creator_alias=args.creator_alias,
                status=calibration_status,
            )
            activation = models.Event(
                date=calibration_date + timedelta(hours=1),
                creator_id=args.creator_id,
                creator_alias=args.creator_alias,
                status=activation_status,
            )
            kit.add_event(calibration)
            kit.add_event(activation)

            kit.calibration_next = calibration_date + relativedelta(years=CALIBRATION_FREQUENCIES_YEARS['marlink'])

            db_session.add_all([kit, base, telecardia, calibration, activation])


if __name__ == '__main__':
    main()
