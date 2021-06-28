import itertools

import arrow
import transaction
from celery.utils.log import get_task_logger
from parsys_utilities.celery_app import app
from parsys_utilities.celery_tasks import get_session_factory
from sqlalchemy.orm import joinedload

from asset_tracker import models, notifications

logger = get_task_logger(__name__)


@app.task()
def consumables_expiration():
    """Remind involved users about equipment consumables expiration."""
    # To avoid Jan (28,29,30,31) + 1 month = Feb 28, convert months in days.
    expiration_delays = (0, 30, 180)

    # Set up db connection.
    session_factory = get_session_factory()

    with transaction.manager:
        db_session = models.get_tm_session(session_factory, transaction.manager)

        total_assets = 0
        for delay_days in expiration_delays:
            expiration_date = arrow.utcnow().shift(days=delay_days).naive

            equipments = db_session.query(models.Equipment) \
                .join(models.Equipment.consumables) \
                .filter(models.Consumable.expiration_date == expiration_date) \
                .options(
                    joinedload(models.Equipment.asset).joinedload(models.Asset.tenant),
                    joinedload(models.Equipment.family),
                    joinedload(models.Equipment.consumables).joinedload(models.Consumable.family),
                ) \
                .all()

            for equipment in equipments:
                notifications.assets.consumables_expiration(
                    app.conf.tenant_config, equipment, expiration_date, delay_days
                )

            total_assets += len(equipments)

        return total_assets


@app.task()
def next_calibration(months=3):
    """Remind the assets owner about planned calibration.

    Args:
        months (int): a reminder is sent x months before a calibration is needed.
    """
    # To avoid Jan (28,29,30,31) + 1 month = Feb 28, convert months in days.
    calibration_date = arrow.utcnow().shift(days=months * 30).naive

    # Set up db connection.
    session_factory = get_session_factory()

    with transaction.manager:
        db_session = models.get_tm_session(session_factory, transaction.manager)

        # Assets that need calibration.
        assets = db_session.query(models.Asset) \
            .filter(models.Asset.calibration_next == calibration_date) \
            .join(models.Asset.tenant) \
            .order_by(models.Tenant.tenant_id, models.Asset.asset_id) \
            .all()

        if not assets:
            return

        # Group assets by tenant.
        groupby_tenant = itertools.groupby(assets, key=lambda asset: asset.tenant.tenant_id)

        for tenant_id, assets in groupby_tenant:
            notifications.assets.next_calibration(app.conf.tenant_config, tenant_id, assets, calibration_date)

        return len(assets)
