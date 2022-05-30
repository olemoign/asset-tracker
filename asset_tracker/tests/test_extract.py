import csv
import os
import random
import tempfile
from datetime import datetime, timedelta

from parsys_utilities.security import Right
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from asset_tracker.constants import ASSET_TYPES
from asset_tracker.models import Tenant, Asset, Event, EventStatus
from asset_tracker.tests import FunctionalTest


class TestExtract(FunctionalTest):
    principals = [Right(name='assets-extract', tenant='tenantXX')]

    @staticmethod
    def populate_data(request):
        session = request.db_session
        events_status = [
            (1, 'stock_parsys', 1, 'In stock Parsys', 'event', 'Parsys - In stock'),
            (2, 'transit_distributor', 2, 'In transit to distributor', 'event',
             'Parsys - In transit to Marlink Logistics'),
            (3, 'stock_distributor', 3, 'In stock distributor', 'event', 'Marlink Logistics - In stock'),
            (4, 'transit_customer', 4, 'In transit to customer', 'event', 'Marlink Logistics - In transit to customer'),
            (5, 'on_site', 5, 'On site', 'event', 'CCTS - On site'),
            (6, 'service', 6, 'In service', 'event', 'CCTS - In service'),
            (7, 'replacement_failure', 7, 'Replacement ordered (failure)', 'event',
             'CCTS - Replacement ordered (failure)'),
            (8, 'replacement_calibration', 8, 'Replacement ordered (calibration)', 'event',
             'CCTS - Replacement ordered (calibration)'),
            (9, 'transit_distributor_return', 9, 'In transit to distributor (return)', 'event',
             'CCTS - In transit to Marlink Logistics'),
            (10, 'transit_parsys', 10, 'In transit to Parsys', 'event', 'Marlink Logistics - In transit to Parsys'),
            (11, 'calibration', 11, 'In calibration', 'event', 'Parsys - In calibration'),
            (12, 'repair', 12, 'In repair', 'event', 'Parsys - In repair'),
            (13, 'decommissioned', 13, 'Decommissioned', 'event', 'Parsys - Decommissioned'),
        ]

        for evt in events_status:
            event_status = EventStatus(id=evt[0], status_id=evt[1], _label=evt[3], position=evt[2], status_type=evt[4],
                                       _label_marlink=evt[5])
            session.add(event_status)

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
                    nb_asset -= 1
        assert nb_asset == 0
        os.remove(tmp_file)
