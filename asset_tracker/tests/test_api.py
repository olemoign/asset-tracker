from pathlib import Path
from unittest.mock import patch

from parsys_utilities.security import Right

from asset_tracker.tests import FunctionalTest


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
        res = self.app.get('/api/update/', params=params, status=200)
        assert res.json_body['updateAvailable'] is True
        assert res.json_body['version'] == '3.0.5-rc2'
        assert (
            res.json_body['url'] == 'https://localhost:80/api/download/medcapture/ParsysMedCaptureSetup-3.0.5-rc2.exe'
        )
