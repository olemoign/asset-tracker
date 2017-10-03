"""Generic views (status, 404, 500) + views tools (headers and templates global variables)."""
from datetime import datetime
from traceback import format_exc

import pkg_resources
from parsys_utilities.authorization import rights_without_tenants
from parsys_utilities.sentry import sentry_capture_exception
from parsys_utilities.status import status_endpoint
from pyramid.events import BeforeRender, NewResponse, subscriber
from pyramid.settings import asbool, aslist
from pyramid.view import exception_view_config, notfound_view_config, view_config

from asset_tracker import models
from asset_tracker.constants import GLUCOMETER_ID

DEFAULT_BRANDING = 'parsys_cloud'


@subscriber(NewResponse)
def add_app_version_header(event):
    """App version header is added to all responses."""
    asset_tracker_version = pkg_resources.require(__package__)[0].version
    event.response.headers.add('X-Parsys-Version', asset_tracker_version)


@subscriber(BeforeRender)
def add_global_variables(event):
    """Templating global variables: these variables are added to all render() calls."""
    event['cloud_name'] = event['request'].registry.settings['asset_tracker.cloud_name']
    event['branding'] = event['request'].registry.settings.get('asset_tracker.branding', DEFAULT_BRANDING)
    event['client_specific'] = aslist(event['request'].registry.settings.get('asset_tracker.client_specific', []))
    event['csrf_token'] = event['request'].session.get_csrf_token()

    event['principals'] = event['request'].effective_principals
    event['principals_without_tenants'] = rights_without_tenants(event['request'].effective_principals)
    event['locale'] = event['request'].locale_name

    event['GLUCOMETER_ID'] = GLUCOMETER_ID

    if event['request'].user:
        event['authenticated_user'] = event['request'].user


@view_config(route_name='status', request_method='GET', renderer='json')
def status_get(request):
    """Check status of service.
    Choose a db table to be queried by status api for availability testing.

    """
    # noinspection PyTypeChecker
    return status_endpoint(
        request=request,
        caller_package=__package__,
        caller_model=models.Asset,
        check_rta=True,
    )


@notfound_view_config(append_slash=True, renderer='errors/404.html')
def not_found_get(request):
    request.response.status_int = 404
    return {}


@exception_view_config(Exception, renderer='errors/500.html')
def exception_view(request):
    """Catch exceptions.
    In all cases, send them to Sentry if the configuration exists.
    In dev reraise them to be caught by pyramid_debugtoolbar.
    In production log them then return a 500 page to the user.

    """
    sentry_capture_exception(request)

    # In dev.
    debug_exceptions = asbool(request.registry.settings.get('asset_tracker.dev.debug_exceptions', False))
    if debug_exceptions:
        raise request.exception

    # In production.
    else:
        error_header = 'Time: {}\nUrl: {}\nMethod: {}\n'.format(datetime.utcnow(), request.url, request.method)
        error_text = error_header + format_exc()
        request.logger_technical.error(error_text)

        request.response.status_int = 500
        return {}


def includeme(config):
    config.add_route(pattern='status/', name='status')
