from paste.translogger import TransLogger
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.config import Configurator
from pyramid.session import SignedCookieSessionFactory
from sqlalchemy import engine_from_config
from sqlalchemy.orm import sessionmaker
from zope.sqlalchemy import register

from .utilities.domain_model import Model


def get_user(request):
    return request.session.get('user')


def user_locale(request):
    if request.user is not None:
        return request.user['locale']


def effective_principals(userid, request):
    if request.user:
        return ['r:' + right for right in request.user['rights']]


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application."""
    assert(settings.get('rta.server_url'))
    assert(settings.get('rta.client_id'))
    assert(settings.get('rta.secret'))

    engine = engine_from_config(settings, 'sqlalchemy.')
    maker = sessionmaker()
    register(maker)
    maker.configure(bind=engine)
    Model.metadata.bind = engine

    config = Configurator(settings=settings, locale_negotiator=user_locale)
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

    cookie_signature = settings['asset_tracker.cookie_signature']
    authenticationn_policy = AuthTktAuthenticationPolicy(cookie_signature, callback=effective_principals, hashalg='sha512')
    authorization_policy = ACLAuthorizationPolicy()
    config.set_authentication_policy(authenticationn_policy)
    config.set_authorization_policy(authorization_policy)

    config.set_session_factory(SignedCookieSessionFactory(cookie_signature))

    config.add_request_method(get_user, 'user', reify=True)
    config.add_request_method(lambda request: maker(), 'db_session', reify=True)

    rta_url = settings['rta.server_url'] + '/{path}'
    config.add_route('rta', rta_url)

    config.include('asset_tracker.api', route_prefix='api')
    config.include('asset_tracker.views')
    config.scan()

    # config.include('pyramid_assetviews')
    # config.add_asset_views('asset_tracker:static', filenames=['apple-touch-icon.png', 'favicon.ico', '.htaccess', 'robots.txt'], http_cache=3600)

    if settings.get('asset_tracker.debug') == 'True':
        return TransLogger(config.make_wsgi_app(), setup_console_handler=False)
    else:
        return config.make_wsgi_app()

