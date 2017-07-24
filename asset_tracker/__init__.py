import logging
from functools import partial

import pkg_resources
from parsys_utilities.authorization import get_user, get_effective_principals, get_user_locale, \
    OpenIDConnectAuthenticationPolicy, TenantedAuthorizationPolicy
from parsys_utilities.logging import logger
from parsys_utilities.notifications import Notifier
from paste.translogger import TransLogger
from pyramid.config import Configurator
from pyramid.settings import asbool
from pyramid_redis_sessions import RedisSessionFactory

from asset_tracker.configuration import update_configuration


# noinspection PyUnusedLocal
def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application."""
    assert settings.get('rta.server_url')
    assert settings.get('rta.client_id')
    assert settings.get('rta.secret')
    assert settings.get('asset_tracker.sessions_broker_url')
    assert settings.get('sqlalchemy.url')

    update_configuration(settings)

    config = Configurator(settings=settings, locale_negotiator=get_user_locale)
    config.set_default_csrf_options(require_csrf=True)
    config.include('pyramid_tm')

    config.include('pyramid_jinja2')
    jinja2_settings = {
        'jinja2.directories': 'asset_tracker:templates',
        'jinja2.cache_size': 400,
        'jinja2.bytecode_caching': True,
        'jinja2.filters': {
            'format_date': 'parsys_utilities.dates:format_date',
            'format_datetime': 'parsys_utilities.dates:format_datetime',
            'route_path': 'pyramid_jinja2.filters:route_path_filter',
            'route_url': 'pyramid_jinja2.filters:route_url_filter'
        },
        'jinja2.newstyle': True,
    }
    config.add_settings(jinja2_settings)
    config.add_jinja2_renderer('.html')
    config.add_static_view('static', 'static', cache_max_age=3600)
    config.add_translation_dirs('asset_tracker:locale')

    cookie_signature = settings['asset_tracker.cookie_signature']
    authentication_callback = partial(get_effective_principals, allow_admins=True)
    authentication_policy = OpenIDConnectAuthenticationPolicy(callback=authentication_callback, authorize_services=True)
    authorization_policy = TenantedAuthorizationPolicy()
    config.set_authentication_policy(authentication_policy)
    config.set_authorization_policy(authorization_policy)

    sessions_broker_url = settings['asset_tracker.sessions_broker_url']
    secure_cookies = not asbool(settings.get('asset_tracker.dev.disable_secure_cookies', False))
    session_factory = RedisSessionFactory(cookie_signature, url=sessions_broker_url, cookie_secure=secure_cookies,
                                          cookie_name='asset_tracker_session')
    config.set_session_factory(session_factory)

    config.add_request_method(get_user, 'user', reify=True)
    config.add_request_method(partial(logger, name='asset_tracker_actions'), 'logger_actions', reify=True)
    config.add_request_method(partial(logger, name='asset_tracker_technical'), 'logger_technical', reify=True)
    send_notifications = not asbool(settings.get('asset_tracker.dev.disable_notifications', False))
    config.add_request_method(partial(Notifier, send_notifications=send_notifications), 'notifier', reify=True)

    config.include('asset_tracker.models')
    config.include('asset_tracker.api', route_prefix='api')
    config.include('asset_tracker.views_asset')
    config.include('asset_tracker.views_utilities')
    config.scan()

    config.include('parsys_utilities.openid_client')
    config.scan('parsys_utilities.openid_client')

    rta_url = settings['rta.server_url'] + '/{path}'
    config.add_route('rta', rta_url)

    config.include('pyramid_assetviews')
    config.add_asset_views('asset_tracker:static', filenames=['.htaccess', 'robots.txt'], http_cache=3600)

    asset_tracker_version = pkg_resources.require(__package__)[0].version
    logging.getLogger('asset_tracker_actions').info('Starting asset tracker version %s', asset_tracker_version)

    log_requests = asbool(settings.get('asset_tracker.dev.log_requests', False))
    if log_requests:
        return TransLogger(config.make_wsgi_app(), setup_console_handler=False)
    else:
        return config.make_wsgi_app()
