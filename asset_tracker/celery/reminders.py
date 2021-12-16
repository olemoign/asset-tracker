import itertools

import arrow
from parsys_utilities.celery import app
from pyramid.threadlocal import get_current_request
from sqlalchemy.orm import joinedload

from asset_tracker import models, notifications


@app.task()
def consumables_expiration():
    """Remind involved users about equipment consumables expiration."""
    request = get_current_request()

    # To avoid Jan (28,29,30,31) + 1 month = Feb 28, convert months in days.
    expiration_delays = (0, 30, 180)

    total_assets = 0
    for delay_days in expiration_delays:
        expiration_date = arrow.utcnow().shift(days=delay_days).naive

        equipments = request.db_session.query(models.Equipment) \
            .join(models.Equipment.consumables) \
            .filter(models.Consumable.expiration_date == expiration_date) \
            .options(
                joinedload(models.Equipment.asset).joinedload(models.Asset.tenant),
                joinedload(models.Equipment.family),
                joinedload(models.Equipment.consumables).joinedload(models.Consumable.family),
            ) \
            .all()

        for equipment in equipments:
            tenant_id = equipment.asset.tenant_id
            notifications.assets.consumables_expiration(request, tenant_id, equipment, expiration_date, delay_days)

        total_assets += len(equipments)

    return total_assets


@app.task()
def next_calibration(months=3):
    """Remind the assets' owner about planned calibration.

    Args:
        months (int): a reminder is sent x months before a calibration is needed.
    """
    request = get_current_request()

    # To avoid Jan (28,29,30,31) + 1 month = Feb 28, convert months in days.
    calibration_date = arrow.utcnow().shift(days=months * 30).naive

    # Assets that need calibration.
    assets = request.db_session.query(models.Asset) \
        .join(models.Asset.tenant) \
        .filter(models.Asset.calibration_next == calibration_date) \
        .order_by(models.Tenant.tenant_id, models.Asset.asset_id) \
        .all()

    if not assets:
        return

    # Group assets by tenant.
    groupby_tenant = itertools.groupby(assets, key=lambda asset: asset.tenant.tenant_id)

    for tenant_id, assets in groupby_tenant:
        notifications.assets.next_calibration(request, tenant_id, assets, calibration_date)

    return len(assets)
