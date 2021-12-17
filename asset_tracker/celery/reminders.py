import itertools

import arrow
from parsys_utilities.celery import app
from pyramid.threadlocal import get_current_request
from sqlalchemy.orm import joinedload

from asset_tracker import models, notifications


@app.task()
def assets_calibration(months=3):
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

    # groupby will transform the list, so we need to check its length now.
    assets_number = len(assets)

    # Group assets by tenant.
    groupby_tenant = itertools.groupby(assets, key=lambda asset: asset.tenant.tenant_id)

    for tenant_id, assets in groupby_tenant:
        notifications.assets.assets_calibration(request, tenant_id, assets, calibration_date)

    return assets_number


@app.task()
def consumables_expiration():
    """Remind involved users about equipment consumables expiration."""
    request = get_current_request()

    # To avoid Jan (28,29,30,31) + 1 month = Feb 28, convert months in days.
    expiration_delays = (0, 30, 180)

    total_assets = 0
    for delay_days in expiration_delays:
        expiration_date = arrow.utcnow().shift(days=delay_days).naive

        assets = request.db_session.query(models.Asset, models.Consumable) \
            .join(models.Asset.tenant) \
            .join(models.Asset.equipments) \
            .join(models.Equipment.consumables) \
            .filter(models.Consumable.expiration_date == expiration_date) \
            .options(
                joinedload(models.Asset.equipments).joinedload(models.Equipment.family),
                joinedload(models.Consumable.family),
            ) \
            .order_by(models.Tenant.tenant_id, models.Asset.asset_id) \
            .all()

        if not assets:
            continue

        # Group assets by tenant.
        groupby_asset = {}
        for asset, consumable in assets:
            if asset.asset_id not in groupby_asset:
                groupby_asset[asset.asset_id] = {'asset': asset, 'consumables': [consumable]}
            else:
                groupby_asset[asset.asset_id]['consumables'].append(consumable)

        total_assets += len(groupby_asset)

        groupby_tenant = {}
        for asset_dict in groupby_asset.values():
            tenant_id = asset_dict['asset'].tenant.tenant_id
            if tenant_id not in groupby_tenant:
                groupby_tenant[tenant_id] = [asset_dict]
            else:
                groupby_tenant[tenant_id].append(asset_dict)

        for tenant_id, assets in groupby_tenant.items():
            notifications.assets.consumables_expiration(request, tenant_id, assets, expiration_date, delay_days)

    return total_assets
