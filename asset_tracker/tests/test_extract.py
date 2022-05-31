import csv
import json
import os
import random
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from parsys_utilities.security import Right
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from asset_tracker.config import update_statuses, update_consumable_families, update_equipment_families
from asset_tracker.constants import ASSET_TYPES
from asset_tracker.models import Tenant, Asset, Event, EventStatus
from asset_tracker.tests import FunctionalTest


class TestExtract(FunctionalTest):
    principals = [Right(name='assets-extract', tenant='tenantXX')]

    @staticmethod
    def populate_data(request):
        session = request.db_session
        with open(os.path.join('..', Path(os.path.dirname(__file__)).parent, 'config.json')) as config_file:
            config = json.load(config_file)

        update_equipment_families(session, config)
        update_consumable_families(session, config)
        update_statuses(session, config)

        now = datetime.now()
        status = session.query(EventStatus).order_by(EventStatus.position.asc()).first()
        for i in range(1, 3):
            tenant = Tenant(tenant_id=f'tenant{i}', name=f'Tenant {i}')
            session.add(tenant)
            for j in range(1, 5):
                asset_type = list(ASSET_TYPES.keys())[random.randint(0, len(ASSET_TYPES) - 1)]
                asset = Asset(asset_id=f'asset_{i}_{j}', tenant=tenant, user_id='user',
                              asset_type=asset_type, status=status)
                session.add(asset)
                for event_status in session.query(EventStatus).order_by(EventStatus.position).all():
                    event = Event(event_id=f'evt_{i}_{j}_{event_status.position}', asset=asset,
                                  date=now + timedelta(days=i*10 + j + event_status.position), creator_id='user',
                                  removed=False, status=event_status, creator_alias='user')
                    asset.status = event_status
                    if event_status.status_id == 'software_update':
                        event.extra = json.dumps({'software_name': 'test_soft', 'software_version': '1.0'})
                    session.add(event)
        session.flush()

    def test_extract_asset(self):
        ROOT_URL = '/assets/extract/'
        request = self.dummy_request()
        TestExtract.populate_data(request)
        request.db_session.commit()
        response = self.app.get(ROOT_URL)
        assert response is not None and response.body is not None
        tmp_file = tempfile.mktemp(suffix='.csv')
        with open(tmp_file, 'w+') as f:
            f.write(response.body.decode('UTF-8'))

        nb_asset = request.db_session.query(Asset).count()
        with open(tmp_file, 'r') as f:
            header = None
            reader = csv.reader(f)
            for row in reader:
                if not header:
                    header = row
                    assert 'last_status_change_date' in header
                    assert 'software_1_name' in header
                    assert 'software_1_version' in header
                else:
                    if len(row) <= 0:
                        continue
                    asset = request.db_session.query(Asset).options(joinedload(Asset.tenant), joinedload(Asset.site),
                                                                    joinedload(Asset.status)
                                                                    ).filter(Asset.asset_id == row[0]).one()

                    assert asset.asset_type == row[1]
                    assert asset.tenant.tenant_id == row[2]
                    assert asset.tenant.name == row[3]
                    assert asset.status.label(None) == row[8]
                    assert request.db_session\
                           .query(func.max(Event.created_at)).filter(Event.asset_id == asset.id).one()[0] == datetime\
                           .strptime(row[9], '%Y-%m-%d %H:%M:%S')
                    assert asset.production == datetime.strptime(row[11], '%Y-%m-%d').date()
                    assert asset.delivery == datetime.strptime(row[12], '%Y-%m-%d').date()
                    assert asset.activation == datetime.strptime(row[13], '%Y-%m-%d').date()
                    if not asset.calibration_last:
                        assert len(row[14]) == 0
                    else:
                        assert asset.calibration_last == datetime.strptime(row[14], '%Y-%m-%d').date()
                    assert row[22] == 'test_soft'
                    assert row[23] == '1.0'
                    nb_asset -= 1
        assert nb_asset == 0
        os.remove(tmp_file)
