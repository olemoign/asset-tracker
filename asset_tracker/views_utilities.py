from datetime import datetime
from traceback import format_exc

import pkg_resources
import raven
from parsys_utilities.authorization import rights_without_tenants
from parsys_utilities.status import status_endpoint
from pyramid.events import BeforeRender, NewResponse, subscriber
from pyramid.settings import asbool, aslist
from pyramid.view import exception_view_config, notfound_view_config, view_config

from asset_tracker import models

DEFAULT_BRANDING = 'parsys_cloud'


@subscriber(NewResponse)
def add_app_version_header(event):
    asset_tracker_version = pkg_resources.require(__package__)[0].version
    event.response.headers.add('X-Parsys-Version', asset_tracker_version)


@subscriber(BeforeRender)
def add_global_variables(event):
    event['cloud_name'] = event['request'].registry.settings['asset_tracker.cloud_name']
    event['branding'] = event['request'].registry.settings.get('asset_tracker.branding', DEFAULT_BRANDING)
    event['client_specific'] = aslist(event['request'].registry.settings.get('asset_tracker.client_specific', []))
    event['csrf_token'] = event['request'].session.get_csrf_token()

    event['principals'] = event['request'].effective_principals
    event['principals_without_tenants'] = rights_without_tenants(event['request'].effective_principals)
    event['locale'] = event['request'].locale_name

    if event['request'].user:
        event['user_alias'] = event['request'].user['alias']


@view_config(route_name='status-endpoint', request_method='GET', renderer='json')
def status_get(request):
    """Check current status of asset_tracker service.
    Choose a local model to be queried by status api for availability testing.

    """

    return status_endpoint(
        request=request,
        caller_package=__package__,
        caller_model=models.Asset,
        check_rta=True,
        check_celery=False
    )


@notfound_view_config(append_slash=True, renderer='errors/404.html')
def not_found_get(request):
    request.response.status_int = 404
    return {}


@exception_view_config(Exception, renderer='errors/500.html')
def exception_view(request):
    """Catch exceptions.
    In dev reraise them to be caught by pyramid_debugtoolbar.
    In production log them, send them to Sentry then return a 500 page to the user.

    """
    # In dev.
    debug_exceptions = asbool(request.registry.settings.get('asset_tracker.dev.debug_exceptions', False))
    if debug_exceptions:
        raise request.exception

    # In production.
    else:
        error_header = 'Time: {}\nUrl: {}\nMethod: {}\n'.format(datetime.utcnow(), request.url, request.method)
        error_text = error_header + format_exc()
        request.logger_technical.error(error_text)

        sentry_dsn = request.registry.settings['asset_tracker.sentry_dsn']
        sentry_client = raven.Client(sentry_dsn)
        sentry_client.captureException()

        request.response.status_int = 500
        return {}


def includeme(config):
    config.add_route(pattern='status/', name='status-endpoint')
