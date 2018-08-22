from urllib.parse import urlparse

from asset_tracker.tests import BaseTest


# noinspection PyTypeChecker
class Login(BaseTest):
    def test_simple(self):
        res = self.app.get('/', status=302)
        assert urlparse(res.location).netloc == 'localhost:6544'
