from datetime import date
from pathlib import Path
from unittest.mock import patch

from parsys_utilities.security import Right

from asset_tracker.models import Asset, Event, EventStatus, Tenant
from asset_tracker.tests import FunctionalTest


def create_asset(request):
    tenant = Tenant(tenant_id='tenantXX', name='Tenant XX')
    status_created = EventStatus(
        status_id='stock_parsys', position=1, status_type='event', _label='In stock Parsys'
    )
    status_software = EventStatus(
        status_id='software_update', position=14, status_type='config', _label='Software update'
    )
    asset = Asset(asset_id='x@x.x', asset_type='station', status=status_created, tenant=tenant)
    event_created = Event(
        asset=asset, date=date.today(), creator_id='XXXXXXXX', creator_alias='XXXX XXXX', status=status_created
    )
    request.db_session.add_all([asset, event_created, status_created, status_software, tenant])
    request.db_session.commit()


class API(FunctionalTest):
    principals = [Right(name='api-software-update', tenant='tenantXX')]

    @patch('asset_tracker.api.software.Path.is_dir', return_value=True)
    @patch('asset_tracker.api.software.get_product_files')
    def test_software_get(self, get_product_files_mock, _is_dir_mock):
        get_product_files_mock.return_value = [
            Path('/tmp/ParsysMedCaptureSetup-3.1.0-alpha11.exe'),
            Path('/tmp/ParsysMedCaptureSetup-3.0.5-rc2.exe'),
            Path('/tmp/ParsysMedCaptureSetup-3.0.2.exe'),
        ]

        params = {'product': 'medcapture', 'current': '2.9.4'}
        response = self.app.get('/api/update/', params=params, status=200)
        output = response.json_body
        assert output['updateAvailable'] is True
        assert output['version'] == '3.0.5-rc2'
        assert output['url'] == 'https://localhost:80/api/download/medcapture/ParsysMedCaptureSetup-3.0.5-rc2.exe'

    def test_software_post(self):
        request = self.dummy_request()
        create_asset(request)

        self.app.post_json('/api/update/?product=medcapture', {'version': '2.9.4'}, status=200)

        asset = request.db_session.query(Asset).filter_by(asset_id='x@x.x').first()
        update = asset.history('desc') \
            .join(Event.status) \
            .filter(EventStatus.status_id == 'software_update') \
            .first()
        assert update.extra_json['software_name'] == 'medcapture'
        assert update.extra_json['software_version'] == '2.9.4'
