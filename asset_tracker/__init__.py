from json import load
from paste.translogger import TransLogger
from pkg_resources import resource_string

from pyramid.config import Configurator
from pyramid.session import SignedCookieSessionFactory
from pyramid.settings import asbool
from sqlalchemy import engine_from_config
from sqlalchemy.orm import sessionmaker
from transaction import manager
from zope.sqlalchemy import register

from .models import EquipmentFamily
from .utilities.authorization import Right, RTAAuthenticationPolicy, TenantedAuthorizationPolicy
from .utilities.domain_model import Model


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
    debug_mode = asbool(settings.get('asset_tracker.debug'))

    engine = engine_from_config(settings, 'sqlalchemy.')
    maker = sessionmaker()
    register(maker)
    maker.configure(bind=engine)
    Model.metadata.bind = engine

    with manager:
        db_session = maker()
        db_session.query(EquipmentFamily).delete()
        with open(resource_string(__name__, 'equipments_families.json')) as families_list:
            json_families = load(families_list)
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
    config.add_translation_dirs('asset_tracker:locale')

    cookie_signature = settings['open_id.cookie_signature']
    authentication_policy = RTAAuthenticationPolicy(cookie_signature, cookie_name='parsys_cloud_auth_tkt',
                                                    secure=not debug_mode, callback=get_effective_principals,
                                                    http_only=True, wild_domain=False, hashalg='sha512')
    authorization_policy = TenantedAuthorizationPolicy()
    config.set_authentication_policy(authentication_policy)
    config.set_authorization_policy(authorization_policy)

    config.set_session_factory(SignedCookieSessionFactory(cookie_signature))

    config.add_request_method(get_user, 'user', reify=True)
    config.add_request_method(lambda request: maker(), 'db_session', reify=True)

    rta_url = settings['rta.server_url'] + '/{path}'
    config.add_route('rta', rta_url)

    config.include('asset_tracker.api', route_prefix='api')
    config.include('asset_tracker.views')
    config.scan()

    config.include('py_openid_connect.openid_connect_client')
    config.scan('py_openid_connect')

    config.include('pyramid_assetviews')
    config.add_asset_views('asset_tracker:static', filenames=['.htaccess', 'robots.txt'], http_cache=3600)

    if settings.get('asset_tracker.debug') == 'True':
        return TransLogger(config.make_wsgi_app(), setup_console_handler=False)
    else:
        return config.make_wsgi_app()

