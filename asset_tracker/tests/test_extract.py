import csv
import json
import os
import random
import tempfile
from datetime import date, datetime, timedelta
from parsys_utilities.security import Right
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from asset_tracker.config import update_statuses, update_consumable_families, update_equipment_families
from asset_tracker.constants import ASSET_TYPES, PATH
from asset_tracker.models import Asset, Event, EventStatus, Tenant
from asset_tracker.tests import FunctionalTest


class Extract(FunctionalTest):
    principals = [Right(name='assets-extract', tenant='tenantXX')]

    @staticmethod
    def populate_data(request):
        with open(PATH / 'config.json') as config_file:
            config = json.load(config_file)

        update_equipment_families(request.db_session, config)
        update_consumable_families(request.db_session, config)
        update_statuses(request.db_session, config)

        today = date.today()
        status = request.db_session.query(EventStatus).order_by(EventStatus.position).first()
        events_status = request.db_session.query(EventStatus).order_by(EventStatus.position).all()

        for i in range(1, 3):
            tenant = Tenant(tenant_id=f'tenant{i}', name=f'Tenant {i}')
            request.db_session.add(tenant)

            for j in range(1, 5):
                asset_type = list(ASSET_TYPES.keys())[random.randint(0, len(ASSET_TYPES) - 1)]
                asset = Asset(
                    asset_id=f'asset_{i}_{j}', tenant=tenant, user_id='user', asset_type=asset_type, status=status
                )
                request.db_session.add(asset)

                for event_status in events_status:
                    event = Event(
                        event_id=f'event_{i}_{j}_{event_status.position}',
                        asset=asset,
                        date=today + timedelta(days=i * 10 + j + event_status.position),
                        creator_id='user',
                        creator_alias='user',
                        status=event_status,
                    )
                    if event_status.status_type == 'event':
                        asset.status = event_status
                    elif event_status.status_id == 'software_update':
                        event.extra = json.dumps({'software_name': 'test_soft', 'software_version': '1.0'})
                    request.db_session.add(event)

        request.db_session.commit()

    def test_extract_asset(self):
        request = self.dummy_request()
        self.populate_data(request)

        response = self.app.get('/assets/extract/', status=200)
        tmp_file = tempfile.mktemp(suffix='.csv')
        with open(tmp_file, 'w+') as f:
            f.write(response.body.decode('utf-8'))

        nb_asset = request.db_session.query(Asset).count()
        with open(tmp_file, 'r') as f:
            for index, row in enumerate(csv.reader(f)):
                if index == 0:
                    assert 'last_status_change_date' in row
                    assert 'software_1_name' in row
                    assert 'software_1_version' in row
                    continue

                asset = request.db_session.query(Asset) \
                    .options(joinedload(Asset.tenant), joinedload(Asset.site), joinedload(Asset.status)) \
                    .filter(Asset.asset_id == row[0]) \
                    .one()
                last_status_change = request.db_session.query(func.max(Event.created_at)) \
                    .filter(Event.asset_id == asset.id) \
                    .one()[0]

                assert asset.asset_type == row[1]
                assert asset.tenant.tenant_id == row[2]
                assert asset.tenant.name == row[3]
                assert asset.status.label('parsys') == row[8]
                assert last_status_change == datetime.fromisoformat(row[9])
                assert asset.production == date.fromisoformat(row[11])
                assert asset.delivery == date.fromisoformat(row[12])
                assert asset.activation == date.fromisoformat(row[13])
                if asset.asset_type == 'consumables_case':
                    assert not row[14]
                else:
                    assert asset.calibration_last == date.fromisoformat(row[14])
                assert row[22] == 'test_soft'
                assert row[23] == '1.0'

                nb_asset -= 1

        assert nb_asset == 0
        os.remove(tmp_file)
