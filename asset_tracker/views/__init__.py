from parsys_utilities.authorization import rights_without_tenants
from pyramid.events import BeforeRender, NewResponse, subscriber
from pyramid.settings import aslist

from asset_tracker.constants import ASSET_TRACKER_VERSION, DEFAULT_BRANDING, GLUCOMETER_ID


@subscriber(NewResponse)
def add_app_version_header(event):
    """App version header is added to all responses."""
    event.response.headers.add('X-Parsys-Version', ASSET_TRACKER_VERSION)


@subscriber(BeforeRender)
def add_global_variables(event):
    """Templating global variables: these variables are added to all render() calls."""
    event['cloud_name'] = event['request'].registry.settings['asset_tracker.cloud_name']
    event['branding'] = event['request'].registry.settings.get('asset_tracker.branding', DEFAULT_BRANDING)
    event['client_specific'] = aslist(event['request'].registry.settings.get('asset_tracker.specific', []))
    event['csrf_token'] = event['request'].session.get_csrf_token()

    event['principals'] = event['request'].effective_principals
    event['principals_without_tenants'] = rights_without_tenants(event['request'].effective_principals)
    event['locale'] = event['request'].locale_name

    event['GLUCOMETER_ID'] = GLUCOMETER_ID


def includeme(config):
    config.include('asset_tracker.views.assets')
    config.include('asset_tracker.views.sites')
    config.include('asset_tracker.views.utilities')
