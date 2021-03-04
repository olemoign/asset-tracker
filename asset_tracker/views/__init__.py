from parsys_utilities.authorization import get_tenantless_principals
from pyramid.events import BeforeRender, NewRequest, NewResponse, subscriber
from sentry_sdk import configure_scope

from asset_tracker.constants import ASSET_TRACKER_VERSION


@subscriber(NewRequest)
def tag_user_for_sentry(event):
    """Tag the user in Sentry."""
    with configure_scope() as scope:
        # noinspection PyDunderSlots,PyUnresolvedReferences
        scope.user = {
            'id': event.request.user.id if event.request.user else None,
            'username': event.request.user.login if event.request.user else None,
        }


@subscriber(NewResponse)
def add_app_version_header(event):
    """App version header is added to all responses."""
    event.response.headers.add('X-Parsys-Version', ASSET_TRACKER_VERSION)


@subscriber(BeforeRender)
def add_global_variables(event):
    """Templating global variables: these variables are added to all render() calls."""
    event['cloud_name'] = event['request'].registry.settings['asset_tracker.cloud_name']
    event['config'] = event['request'].registry.settings.get('asset_tracker.config', 'parsys')

    event['tenantless_principals'] = get_tenantless_principals(event['request'].effective_principals)
    event['locale'] = event['request'].locale_name


class FormException(Exception):
    """Custom exception to handle form validation of Assets and Sites.
    The addditional parameter (log) indicates if logging is required.
    """

    def __init__(self, message, log=True):
        super().__init__(message)
        self.log = log


def includeme(config):
    config.include('asset_tracker.views.assets')
    config.include('asset_tracker.views.extract')
    config.include('asset_tracker.views.sites')
