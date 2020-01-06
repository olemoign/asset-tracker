"""Generic views (status, 404, 500)."""
from datetime import datetime
from traceback import format_exc

from parsys_utilities.status import status_endpoint
from pyramid.settings import asbool
from pyramid.view import exception_view_config, notfound_view_config, view_config

from asset_tracker import models


@view_config(route_name='status', request_method='GET', renderer='json')
def status_get(request):
    """Display app status."""
    # noinspection PyTypeChecker
    return status_endpoint(request, 'asset_tracker', models.Asset)


@notfound_view_config(append_slash=True, renderer='errors/404.html')
def not_found_get(request):
    request.response.status_int = 404
    return {}


@exception_view_config(Exception, renderer='errors/500.html')
def exception_view(request):
    """Catch exceptions.
    In dev reraise them to be caught by pyramid_debugtoolbar/sentry.
    In production log them then return a 500 page to the user, the exception is automatically caught by sentry.
    """
    # In dev.
    debug_exceptions = asbool(request.registry.settings.get('asset_tracker.dev.debug_exceptions', False))
    if debug_exceptions:
        raise request.exception

    # In production.
    else:
        error_header = f'Time: {datetime.utcnow()}\nUrl: {request.url}\nMethod: {request.method}\n'
        error_text = error_header + format_exc()
        request.logger_technical.error(error_text)

        request.response.status_code = 500
        return {}


def includeme(config):
    config.add_route(pattern='status/', name='status')
