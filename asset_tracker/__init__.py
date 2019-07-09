"""ASSET TRACKER app configuration/startup."""

import logging
from functools import partial
from urllib.parse import urljoin

import pkg_resources
import sentry_sdk
from parsys_utilities.authorization import get_user, get_effective_principals, get_user_locale, \
    OpenIDConnectAuthenticationPolicy, TenantedAuthorizationPolicy
from parsys_utilities import celery_app
from parsys_utilities.config import TenantConfigurator
from parsys_utilities.logs import logger
from parsys_utilities.notifications import Notifier
from paste.translogger import TransLogger
from pyramid.config import Configurator
from pyramid.settings import asbool
from pyramid_session_redis import RedisSessionFactory
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.logging import ignore_logger
from sentry_sdk.integrations.pyramid import PyramidIntegration

from asset_tracker.config import update_configuration
from asset_tracker.constants import STATIC_FILES_CACHE, USER_INACTIVITY_MAX

# Celery runs celery.app.
celery = celery_app


def main(global_config, assets_configuration=True, **settings):
    """This function returns a Pyramid WSGI application."""
    assert settings.get('rta.server_url')
    assert settings.get('rta.client_id')
    assert settings.get('rta.secret')
    assert settings.get('asset_tracker.sessions_broker_url')
    assert settings.get('sqlalchemy.url')

    # During tests, the app is created BEFORE the db, so we can't do this.
    if assets_configuration:
        update_configuration(settings)

    # noinspection PyShadowingNames
    config = Configurator(settings=settings, locale_negotiator=get_user_locale)
    config.include('pyramid_tm')

    config.include('pyramid_jinja2')
    jinja2_settings = {
        'jinja2.directories': 'asset_tracker:templates',
        'jinja2.filters': {
            'format_date': 'parsys_utilities.dates:format_date',
            'format_datetime': 'parsys_utilities.dates:format_datetime',
            'route_path': 'pyramid_jinja2.filters:route_path_filter',
            'route_url': 'pyramid_jinja2.filters:route_url_filter',
        },
        'jinja2.newstyle': True,
    }
    config.add_settings(jinja2_settings)
    config.add_jinja2_renderer('.html')

    config.add_translation_dirs('asset_tracker:locale')

    # Add custom csv renderer
    config.add_renderer('csv', 'asset_tracker.renderers.CSVRenderer')

    # Authentication/Authorization policies.
    authentication_policy = OpenIDConnectAuthenticationPolicy(
        callback=partial(get_effective_principals, allow_admins=True),
        authorize_services=True,
    )
    authorization_policy = TenantedAuthorizationPolicy()
    config.set_authentication_policy(authentication_policy)
    config.set_authorization_policy(authorization_policy)

    # Redis sessions configuration.
    cookie_signature = settings['asset_tracker.cookie_signature']
    if settings.get('redis.sessions.callable'):
        session_factory = RedisSessionFactory(cookie_signature, client_callable=settings['redis.sessions.callable'])
    else:
        session_factory = RedisSessionFactory(
            cookie_signature,
            timeout=USER_INACTIVITY_MAX,
            cookie_name='asset_tracker_session',
            cookie_secure=not asbool(settings.get('asset_tracker.dev.disable_secure_cookies', False)),
            url=settings['asset_tracker.sessions_broker_url'],
        )
    config.set_session_factory(session_factory)

    # Add request methods.
    # Add user, authenticated or not.
    config.add_request_method(get_user, 'user', reify=True)

    # Add tenant configurator.
    tenant_configurator = partial(TenantConfigurator, config_file=global_config['__file__'])
    config.add_request_method(tenant_configurator, 'tenant_config', reify=True)

    # Add notifier.
    send_notifications = not asbool(settings.get('asset_tracker.dev.disable_notifications', False))
    config.add_request_method(partial(Notifier, send_notifications=send_notifications), 'notifier', reify=True)

    # Add loggers.
    config.add_request_method(partial(logger, name='asset_tracker_actions'), 'logger_actions', reify=True)
    config.add_request_method(partial(logger, name='asset_tracker_technical'), 'logger_technical', reify=True)

    # Configure Sentry.
    dsn = settings.get('sentry.dsn')
    if dsn:
        sentry_sdk.init(dsn=dsn, integrations=[CeleryIntegration(), PyramidIntegration()], attach_stacktrace=True)
        ignore_logger('asset_tracker_technical')

    config_file = global_config['__file__']
    here = global_config['here']
    celery_app.configure_celery_app(config_file, here=here)

    # Add app routes.
    config.include('asset_tracker.models')
    config.include('asset_tracker.api', route_prefix='api')
    config.include('asset_tracker.extract')
    config.include('asset_tracker.views')
    config.scan(ignore='asset_tracker.tests')

    config.include('parsys_utilities.openid_client')
    config.scan('parsys_utilities.openid_client')

    config.add_route('rta', urljoin(settings['rta.server_url'], '/{path}'))

    config.add_static_view('static', 'static', cache_max_age=STATIC_FILES_CACHE)

    # Serve root static files.
    config.include('pyramid_assetviews')
    config.add_asset_views('asset_tracker:static', filenames=['.htaccess', 'robots.txt'], http_cache=STATIC_FILES_CACHE)

    # Log app version on startup.
    asset_tracker_version = pkg_resources.require(__package__)[0].version
    logging.getLogger('asset_tracker_actions').info('Starting asset tracker version %s', asset_tracker_version)

    # In dev, log requests.
    log_requests = asbool(settings.get('asset_tracker.dev.log_requests', False))
    if log_requests:
        return TransLogger(config.make_wsgi_app(), setup_console_handler=False)
    else:
        return config.make_wsgi_app()
