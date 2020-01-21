import itertools

import arrow
import transaction
from celery.utils.log import get_task_logger
from parsys_utilities.celery_app import app
from parsys_utilities.celery_tasks import get_session_factory
from sentry_sdk import capture_exception
from sqlalchemy.orm import joinedload

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


def notify_expiring_consumables(db_session, delay_days):
    """Get equipments with consumables that will expire and send a notification to involved users.

    Args:
        db_session (sqlalchemy.orm.session.Session): sqlalchemy db session.
        delay_days (int): days before expiration.

    Returns:
        int: number of equipments with expiring consumables.
    """
    expiration_date = arrow.utcnow().shift(days=delay_days).naive

    equipments = db_session.query(models.Equipment) \
        .join(models.Equipment.asset) \
        .join(models.Equipment.consumables) \
        .options(joinedload(models.Equipment.family), joinedload(models.Consumable.family)) \
        .filter(models.Consumable.expiration_date == expiration_date) \
        .all()

    pyramid_config = app.conf.pyramid_config

    for equipment in equipments:
        notifications_assets.consumables_expiration(pyramid_config, equipment, expiration_date, delay_days)

    return len(equipments)


@app.task()
def consumables_expiration():
    """Remind involved users about equipment consumables expiration."""
    try:
        # Validate all mandatory config is present.
        [app.conf.pyramid_config['app:main'][config] for config in MANDATORY_CONFIG]
    except AttributeError as error:
        capture_exception(error)
        logger.error(error)
        return -1

    # To avoid Jan (28,29,30,31) + 1 month = Feb 28, convert months in days.
    expiration_delays = (0, 30, 180)

    # Set up db connection.
    session_factory = get_session_factory()

    with transaction.manager:
        db_session = models.get_tm_session(session_factory, transaction.manager)

        total_assets = 0
        for delay_days in expiration_delays:
            total_assets += notify_expiring_consumables(db_session, delay_days)

        return total_assets


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
    calibration_date = arrow.utcnow().shift(days=months * 30).naive

    # Set up db connection.
    session_factory = get_session_factory()

    with transaction.manager:
        db_session = models.get_tm_session(session_factory, transaction.manager)

        # Assets that need calibration.
        assets = db_session.query(models.Asset) \
            .filter(models.Asset.calibration_next == calibration_date) \
            .order_by(models.Asset.tenant_id) \
            .all()

        if not assets:
            return

        pyramid_config = app.conf.pyramid_config

        # Assets must be sorted by tenant_id.
        groupby_tenant = itertools.groupby(assets, key=lambda asset: asset.tenant_id)

        for tenant_id, assets in groupby_tenant:
            notifications_assets.next_calibration(pyramid_config, tenant_id, assets, calibration_date)

        return len(assets)
