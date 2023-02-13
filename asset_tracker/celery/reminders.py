import itertools
from datetime import date, timedelta

from parsys_utilities.celery import app
from pyramid.threadlocal import get_current_request
from sqlalchemy.orm import joinedload

from asset_tracker import models, notifications


@app.task()
def assets_calibration():
    """Remind the assets' owner about planned calibration."""
    request = get_current_request()

    calibration_date = date.today() + timedelta(days=90)

    # Assets that need calibration.
    assets = request.db_session.query(models.Asset) \
        .join(models.Asset.tenant) \
        .filter(
            ~models.Asset.is_decommissioned,
            models.Asset.calibration_next == calibration_date,
        ) \
        .options(joinedload(models.Asset.site)) \
        .order_by(models.Tenant.tenant_id, models.Asset.asset_id) \
        .all()

    if not assets:
        return 0

    # groupby will transform the list, so we need to check its length now.
    total_assets = len(assets)

    # Group assets by tenant.
    groupby_tenant = itertools.groupby(assets, key=lambda asset: asset.tenant.tenant_id)

    for tenant_id, tenant_assets in groupby_tenant:
        notifications.assets.assets_calibration(request, tenant_id, list(tenant_assets), calibration_date)

    return total_assets


@app.task()
def consumables_expiration():
    """Remind involved users about equipment consumables expiration."""
    request = get_current_request()

    expiration_date = date.today() + timedelta(days=90)

    assets = request.db_session.query(models.Asset, models.Consumable) \
        .join(models.Asset.tenant) \
        .join(models.Asset.equipments) \
        .join(models.Equipment.consumables) \
        .filter(
            ~models.Asset.is_decommissioned,
            models.Consumable.expiration_date == expiration_date,
        ) \
        .options(
            joinedload(models.Asset.equipments).joinedload(models.Equipment.family),
            joinedload(models.Consumable.family),
        ) \
        .order_by(models.Tenant.tenant_id, models.Asset.asset_id) \
        .all()

    if not assets:
        return 0

    # Group consumables by asset.
    groupby_asset = []
    for asset, consumable in assets:
        if not hasattr(asset, 'consumables'):
            asset.consumables = [consumable]
            groupby_asset.append(asset)
        else:
            asset.consumables.append(consumable)

    total_assets = len(groupby_asset)

    # Group assets by tenant.
    groupby_tenant = itertools.groupby(groupby_asset, key=lambda asset: asset.tenant.tenant_id)

    for tenant_id, tenant_assets in groupby_tenant:
        notifications.assets.consumables_expiration(request, tenant_id, list(tenant_assets), expiration_date)

    return total_assets
