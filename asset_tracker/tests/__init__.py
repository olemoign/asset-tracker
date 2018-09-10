import os
import shutil
import tempfile
import unittest

import alembic.command
import alembic.config
from parsys_utilities.model import Model
from pyramid.testing import DummyRequest
from pyramid_redis_sessions.tests import DummyRedis
from webtest import TestApp

import asset_tracker

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'


class BaseTest(unittest.TestCase):
    def setUp(self):
        asset_tracker_path = os.path.dirname(asset_tracker.__file__)
        asset_tracker_root = os.path.dirname(asset_tracker_path)
        config_path = os.path.abspath(os.path.join(asset_tracker_root, 'development.ini'))
        global_config = {'__file__': config_path, 'here': asset_tracker_root}

        self.blob_dir = tempfile.mkdtemp()

        dummy_redis = DummyRedis()

        def get_dummy_redis(_request, **_kw):
            return dummy_redis

        self.ini_settings = {
            'pyramid.csrf_trusted_origins': ['localhost', 'localhost:80', 'localhost:443'],
            'redis.sessions.callable': get_dummy_redis,
            'sqlalchemy.url': 'sqlite:///:memory:',
            'asset_tracker.cookie_signature': 'whydoesitalwaysrainonme',
            'asset_tracker.sessions_broker_url': 'redis://username:password@localhost:6379/0',
            'rta.server_url': 'http://localhost:6544',
            'rta.client_id': 'asset_tracker',
            'rta.secret': 'asset_tracker',
        }

        asset_tracker_app = asset_tracker.main(global_config, assets_configuration=False, **self.ini_settings)

        self.session_factory = asset_tracker_app.registry['db_session_factory']
        self.engine = self.session_factory.kw['bind']

        alembic_cfg = alembic.config.Config()
        alembic_cfg.attributes['engine'] = self.engine
        alembic_cfg.set_main_option('script_location', 'alembic')
        alembic.command.upgrade(alembic_cfg, 'head')

        self.app = TestApp(asset_tracker_app, extra_environ={'wsgi.url_scheme': 'https', 'REMOTE_ADDR': '127.0.0.1'})

    def tearDown(self):
        Model.metadata.drop_all(bind=self.engine)
        shutil.rmtree(self.blob_dir)

    def dummy_request(self):
        request = DummyRequest()
        # request.user = User(is_admin=user_is_admin)
        request.db_session = self.session_factory()
        request.registry.settings = self.ini_settings
        return request
