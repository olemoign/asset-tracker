from pyramid.i18n import TranslationString as _


def assets_calibration(request, tenant_id, assets, calibration_date):
    """Notify an asset owner that the asset needs to be calibrated.

    Args:
        request (pyramid.request.Request).
        tenant_id (str).
        assets (list[asset_tracker.models.Asset]).
        calibration_date (date): precise calibration date (YYYY-MM-DD).
    """

    template_data = {
        'assets': assets,
        'calibration_date': calibration_date,
        'cloud_name': request.registry.settings['asset_tracker.cloud_name'],
    }

    # Email.
    subject = _('Device calibration reminder')
    text = 'emails/assets_calibration.txt'
    html = 'emails/assets_calibration.html'
    emails = request.notifier.render_emails(subject, text, html, template_data)

    # Asynchronous POST.
    request.notifier.notify({
        'message': {'email': emails},
        'rights': ['notifications-calibration'],
        'tenant': tenant_id,
    })

    request.logger_technical.info(['notify calibration date', [asset.id for asset in assets]])


def consumables_expiration(request, tenant_id, equipment, expiration_date, delay_days):
    """Notify users with notifications-consumables right that the consumables of an equipment are expiring.

    Args:
        request (pyramid.request.Request).
        tenant_id (str).
        equipment (asset_tracker.models.Equipment).
        expiration_date (date): consumable expiration date (YYYY-MM-DD).
        delay_days (int): number of days before expiration.
    """
    expired_consumables = []
    for consumable in equipment.consumables:
        if consumable.expiration_date.strftime('%Y-%m-%d') == expiration_date:
            expired_consumables.append(consumable.family.model)

    template_data = {
        'asset': equipment.asset,
        'cloud_name': request.registry.settings['asset_tracker.cloud_name'],
        'delay_days': delay_days,
        'expired_consumables': expired_consumables,
        'expiration_date': expiration_date,
    }

    # Email.
    subject = _('Equipment consumables expiration reminder')
    text = 'emails/consumables_expiration.txt'
    html = 'emails/consumables_expiration.html'
    emails = request.notifier.render_emails(subject, text, html, template_data)
    request.logger_technical.info(emails)

    # Asynchronous POST.
    request.notifier.notify({
        'message': {'email': emails},
        'rights': ['notifications-consumables'],
        'tenant': tenant_id,
    })

    request.logger_technical.info(['notify consumables expiration', equipment.id])
