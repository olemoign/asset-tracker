from json import loads
from paste.translogger import TransLogger
from pkg_resources import resource_string

import transaction
from pyramid.config import Configurator
from pyramid.events import NewResponse, subscriber
from pyramid.session import SignedCookieSessionFactory
from pyramid.settings import asbool

from .models import EquipmentFamily, get_engine, get_session_factory, get_tm_session
from .utilities.authorization import Right, RTAAuthenticationPolicy, TenantedAuthorizationPolicy


@subscriber(NewResponse)
def add_security_headers(event):
    secure_headers = asbool(event.request.registry.settings.get('asset_tracker.dev.secure_headers', True))
    if secure_headers:
        event.response.headers.add('X-Frame-Options', 'deny')
        event.response.headers.add('X-XSS-Protection', '1; mode=block')
        event.response.headers.add('X-Content-Type-Options', 'nosniff')


def get_user(request):
    return request.session.get('user')


def get_user_locale(request):
    if request.user:
        return request.user['locale']


def get_effective_principals(userid, request):
    if request.user:
        if request.user['is_admin']:
            return ['g:admin']
        else:
            return [Right(tenant=item[0], name=item[1]) for item in request.user['rights']]


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application."""
    assert(settings.get('rta.server_url'))
    assert(settings.get('rta.client_id'))
    assert(settings.get('rta.secret'))
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

    config = Configurator(settings=settings, locale_negotiator=get_user_locale)
    config.include('pyramid_tm')

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

    cookie_signature = settings['open_id.cookie_signature']
    secure_cookies = asbool(settings.get('asset_tracker.dev.secure_cookies', True))
    authentication_policy = RTAAuthenticationPolicy(cookie_signature, cookie_name='parsys_cloud_auth_tkt',
                                                    secure=secure_cookies, callback=get_effective_principals,
                                                    http_only=True, wild_domain=False, hashalg='sha512')
    authorization_policy = TenantedAuthorizationPolicy()
    config.set_authentication_policy(authentication_policy)
    config.set_authorization_policy(authorization_policy)

    config.set_session_factory(SignedCookieSessionFactory(cookie_signature))

    config.add_request_method(get_user, 'user', reify=True)

    config.include('.models')
    config.include('asset_tracker.api', route_prefix='api')
    config.include('asset_tracker.views')
    config.scan()

    config.include('py_openid_connect.openid_connect_client')
    config.scan('py_openid_connect')

    rta_url = settings['rta.server_url'] + '/{path}'
    config.add_route('rta', rta_url)

    config.include('pyramid_assetviews')
    config.add_asset_views('asset_tracker:static', filenames=['.htaccess', 'robots.txt'], http_cache=3600)

    log_requests = asbool(settings.get('asset_tracker.dev.log_requests', False))
    if log_requests:
        return TransLogger(config.make_wsgi_app(), setup_console_handler=False)
    else:
        return config.make_wsgi_app()

