from functools import partial
from json import loads
from pkg_resources import resource_string

import transaction
from parsys_utilities.authorization import add_security_headers as basic_security_headers, openid_connect_get_user, \
    openid_connect_get_effective_principals, openid_connect_get_user_locale, OpenIDConnectAuthenticationPolicy, \
    TenantedAuthorizationPolicy
from parsys_utilities.celery_app import app as celery_app
from parsys_utilities.notifications import Notifier
from paste.translogger import TransLogger
from pyramid.config import Configurator
from pyramid.events import NewResponse, subscriber
from pyramid.settings import asbool
from pyramid_redis_sessions import RedisSessionFactory

from .models import EquipmentFamily, get_engine, get_session_factory, get_tm_session


@subscriber(NewResponse)
def add_security_headers(event):
    """ Add https-related security and cross origin xhr headers.

    Args:
        event (pyramid.request.Request): Request.

    """
    secure_headers = asbool(not event.request.registry.settings.get('asset_tracker.dev.disable_secure_headers', False))
    # Deactivate HTTPS-linked headers in dev.
    if secure_headers:
        basic_security_headers(event)


# noinspection PyUnusedLocal
def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application."""
    assert(settings.get('rta.server_url'))
    assert(settings.get('rta.client_id'))
    assert(settings.get('rta.secret'))
    assert settings.get('asset_tracker.sessions_broker_url')
    assert settings.get('sqlalchemy.url')

    with transaction.manager:
        engine = get_engine(settings)
        session_factory = get_session_factory(engine)
        db_session = get_tm_session(session_factory, transaction.manager)

        db_session.query(EquipmentFamily).delete()

        families_list = resource_string(__name__, 'equipments_families.json').decode('utf-8')
        json_families = loads(families_list)
        for json_family in json_families:
            family = EquipmentFamily(id=json_family['id'], model=json_family['model'])
            db_session.add(family)

    config = Configurator(settings=settings, locale_negotiator=openid_connect_get_user_locale)
    config.set_default_csrf_options(require_csrf=True)

    config.include('pyramid_jinja2')
    jinja2_settings = {
        'jinja2.directories': 'asset_tracker:templates',
        'jinja2.cache_size': 400,
        'jinja2.bytecode_caching': True,
        'jinja2.filters': {
            'route_path': 'pyramid_jinja2.filters:route_path_filter',
            'route_url': 'pyramid_jinja2.filters:route_url_filter'
        },
        'jinja2.newstyle': True,
    }
    config.add_settings(jinja2_settings)
    config.add_jinja2_renderer('.html')
    config.add_static_view('static', 'static', cache_max_age=3600)
    # config.add_translation_dirs('asset_tracker:locale')

    cookie_signature = settings['asset_tracker.cookie_signature']
    authentication_policy = OpenIDConnectAuthenticationPolicy(
        callback=partial(openid_connect_get_effective_principals, allow_admins=True))
    authorization_policy = TenantedAuthorizationPolicy()
    config.set_authentication_policy(authentication_policy)
    config.set_authorization_policy(authorization_policy)

    sessions_broker_url = settings['asset_tracker.sessions_broker_url']
    secure_cookies = asbool(not settings.get('asset_tracker.dev.disable_secure_cookies', False))
    session_factory = RedisSessionFactory(cookie_signature, url=sessions_broker_url, cookie_secure=secure_cookies,
                                          cookie_name='asset_tracker_session')
    config.set_session_factory(session_factory)

    config.add_request_method(openid_connect_get_user, 'user', reify=True)
    send_notifications = asbool(not settings.get('asset_tracker.dev.disable_notifications', False))
    config.add_request_method(partial(Notifier, send_notifications=send_notifications), 'notifier', reify=True)

    celery_broker_url = settings.get('celery.broker_url')
    if celery_broker_url:
        celery_app.conf.update(BROKER_URL=celery_broker_url)

    config.include('.models')
    config.include('asset_tracker.api', route_prefix='api')
    config.include('asset_tracker.views')
    config.scan()

    config.include('parsys_utilities.openid_client')
    config.scan('parsys_utilities.openid_client')

    rta_url = settings['rta.server_url'] + '/{path}'
    config.add_route('rta', rta_url)

    config.include('pyramid_assetviews')
    config.add_asset_views('asset_tracker:static', filenames=['.htaccess', 'robots.txt'], http_cache=3600)

    log_requests = asbool(settings.get('asset_tracker.dev.log_requests', False))
    if log_requests:
        return TransLogger(config.make_wsgi_app(), setup_console_handler=False)
    else:
        return config.make_wsgi_app()
