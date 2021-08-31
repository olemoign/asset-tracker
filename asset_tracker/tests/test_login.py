from urllib.parse import urlparse

from asset_tracker.tests import FunctionalTest


class Login(FunctionalTest):
    def test_simple(self):
        res = self.app.get('/', status=302)
        assert urlparse(res.location).netloc == 'localhost:6544'
