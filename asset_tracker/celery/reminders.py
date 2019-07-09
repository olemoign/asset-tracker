import itertools

import arrow
import transaction
from celery.utils.log import get_task_logger
from parsys_utilities.celery_app import app
from parsys_utilities.celery_tasks import get_session_factory
from sentry_sdk import capture_exception

from asset_tracker import models
from asset_tracker.notifications import assets as notifications_assets

MANDATORY_CONFIG = {
    'asset_tracker.cloud_name',
    'asset_tracker.server_url',
    'rta.client_id',
    'rta.secret',
    'rta.server_url',
}

logger = get_task_logger(__name__)


@app.task()
def next_calibration(months=3):
    """Remind the assets owner about planned calibration.

    Args:
        months (int): a reminder is sent x months before a calibration is needed.

    """

    try:
        # Validate all mandatory config is present.
        [app.conf.pyramid_config['app:main'][config] for config in MANDATORY_CONFIG]
    except AttributeError as error:
        capture_exception(error)
        logger.error(error)
        return -1

    # To avoid Jan (28,29,30,31) + 1 month = Feb 28, convert months in days.
    calibration_date = arrow.utcnow().shift(days=months * 30).format('YYYY-MM-DD')

    # Set up db connection.
    session_factory = get_session_factory()

    with transaction.manager:
        db_session = models.get_tm_session(session_factory, transaction.manager)

        # Assets that need calibration.
        assets = db_session.query(models.Asset) \
            .filter(models.Asset.calibration_next == calibration_date) \
            .order_by(models.Asset.tenant_id) \
            .all()

        if assets:
            pyramid_config = app.conf.pyramid_config

            # assets must be sorted by tenant_id
            groupby_tenant = itertools.groupby(assets, key=lambda asset: asset.tenant_id)

            for tenant_id, assets in groupby_tenant:
                notifications_assets.next_calibration(pyramid_config, tenant_id, assets, calibration_date)
