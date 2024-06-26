"""ASSET TRACKER app configuration/startup."""

import logging
from functools import partial
from urllib.parse import urljoin

import sentry_sdk
from depot.manager import DepotManager
from parsys_utilities import STATIC_FILES_CACHE, USER_SESSION_DURATION, celery as celery_utils
from parsys_utilities.config import TenantConfigurator
from parsys_utilities.logs import logger
from parsys_utilities.notifications import Notifier
from parsys_utilities.security.authorization import OpenIDConnectAuthenticationPolicy, TenantedAuthorizationPolicy, \
    get_effective_principals, get_user, get_user_locale
from parsys_utilities.sql import activate_hook
from paste.translogger import TransLogger
from pyramid.config import Configurator
from pyramid.settings import asbool
from pyramid_session_redis import RedisSessionFactory
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.logging import ignore_logger
from sentry_sdk.integrations.pyramid import PyramidIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from asset_tracker.config import DEFAULT_CONFIG, MANDATORY_CONFIG, update_configuration
from asset_tracker.constants import ASSET_TRACKER_VERSION, LOCALES_PATH


def main(global_config, **settings):
    """This function returns a Pyramid WSGI application."""
    technical_logger = logging.getLogger('asset_tracker_technical')

    for app_config in MANDATORY_CONFIG:
        if not settings.get(app_config):
            technical_logger.critical(f'***CRITICAL: Missing mandatory {app_config}.***')

    # During tests, the app is created BEFORE the db, so we can't do this.
    if not settings.get('asset_tracker.tests.disable_configuration', False):
        update_configuration(settings)

    settings['tm.activate_hook'] = activate_hook
    # noinspection PyShadowingNames
    config = Configurator(settings=settings, locale_negotiator=get_user_locale)
    # Activate CSRF check by default.
    config.set_default_csrf_options()
    config.include('pyramid_tm')

    config_file = global_config['__file__']
    config.registry.tenant_config = TenantConfigurator(config_file, defaults=DEFAULT_CONFIG)

    config.include('pyramid_jinja2')
    jinja2_settings = {
        'jinja2.bytecode_caching': True,
        'jinja2.directories': 'asset_tracker:templates',
        'jinja2.filters': {
            'format_date': 'parsys_utilities.dates:format_date',
            'route_path': 'pyramid_jinja2.filters:route_path_filter',
            'route_url': 'pyramid_jinja2.filters:route_url_filter',
        },
        'jinja2.newstyle': True,
    }
    config.add_settings(jinja2_settings)
    config.add_jinja2_renderer('.html')
    config.add_jinja2_renderer('.txt')

    config.add_translation_dirs('asset_tracker:locale')

    # Add CSV renderer.
    config.add_renderer('csv', 'parsys_utilities.renderers.CSVRenderer')

    # Authentication/Authorization policies.
    authentication_policy = OpenIDConnectAuthenticationPolicy(
        callback=partial(get_effective_principals, allow_admins=True), authorize_services=True
    )
    authorization_policy = TenantedAuthorizationPolicy()
    config.set_authentication_policy(authentication_policy)
    config.set_authorization_policy(authorization_policy)

    # Redis sessions configuration.
    cookie_secure = not asbool(settings.get('asset_tracker.dev.disable_secure_cookies', False))
    session_factory = RedisSessionFactory(
        settings['asset_tracker.cookie_signature'],
        timeout=USER_SESSION_DURATION,
        cookie_name='asset_tracker_session',
        cookie_secure=cookie_secure,
        cookie_samesite='None' if cookie_secure else None,
        url=settings['asset_tracker.sessions_broker_url'],
    )
    config.set_session_factory(session_factory)

    # Add request methods.
    # Add user, authenticated or not.
    config.add_request_method(get_user, 'user', reify=True)

    # Add notifier.
    notifier = partial(
        Notifier,
        translation_directories=LOCALES_PATH,
        send_notifications=not asbool(settings.get('asset_tracker.dev.disable_notifications', False)),
    )
    config.add_request_method(notifier, 'notifier', reify=True)

    # Add loggers.
    config.add_request_method(partial(logger, name='asset_tracker_actions'), 'logger_actions', reify=True)
    config.add_request_method(partial(logger, name='asset_tracker_technical'), 'logger_technical', reify=True)

    # Configure Sentry.
    dsn = settings.get('sentry.dsn')
    if dsn:
        sentry_sdk.init(
            attach_stacktrace=True,
            dsn=dsn,
            environment=settings.get('sentry.environment', 'development'),
            in_app_include=['asset_tracker', 'parsys_utilities'],
            integrations=[CeleryIntegration(), PyramidIntegration(), RedisIntegration(), SqlalchemyIntegration()],
            release=ASSET_TRACKER_VERSION,
            send_default_pii=True,
            server_name=settings.get('asset_tracker.server_url', 'configuration_error'),
        )
        ignore_logger('asset_tracker_technical')

    if not DepotManager.get():
        DepotManager.configure('default', {'depot.storage_path': settings.get('asset_tracker.blobstore_path')})

    # Configure Celery.
    broker_url = config.registry.tenant_config.settings['celery']['broker_url']
    celery_utils.configure_celery_producer(broker_url)

    # Add app routes.
    config.include('asset_tracker.models')
    config.include('asset_tracker.api', route_prefix='api')
    config.include('asset_tracker.views')
    config.scan(ignore='asset_tracker.tests')

    config.include('parsys_utilities.security.openid_client')
    config.scan('parsys_utilities.security.openid_client')
    config.include('parsys_utilities.status')
    config.scan('parsys_utilities.status')

    config.add_route('rta', urljoin(settings['rta.server_url'], '/{path}'))

    config.add_static_view('static', 'static', cache_max_age=STATIC_FILES_CACHE)

    # Log app version on startup.
    technical_logger.info(f'Starting asset tracker version {ASSET_TRACKER_VERSION}.')

    # In dev, log requests.
    log_requests = asbool(settings.get('asset_tracker.dev.log_requests', False))
    if log_requests:
        return TransLogger(config.make_wsgi_app(), setup_console_handler=False)
    else:
        return config.make_wsgi_app()
