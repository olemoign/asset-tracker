from pyramid.view import view_config

from asset_tracker import models
from parsys_utilities.status import status_endpoint


@view_config(route_name='status-endpoint', request_method='GET', renderer='json')
def asset_tracker_status(request):
    """
    Check current status of asset_tracker service

    choose a local model to be queried by status api for availability testing
    """

    return status_endpoint(
        request=request,
        caller_package=__package__,
        caller_model=models.EquipmentFamily,
        check_rta=True,
        check_celery=False
    )


def includeme(config):
    config.add_route(pattern='status/', name='status-endpoint')
