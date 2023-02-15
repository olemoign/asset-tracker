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
        'app_url': request.registry.tenant_config.get_for_tenant('asset_tracker.server_url', tenant_id),
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


def consumables_expiration(request, tenant_id, assets, expiration_date, delay_days):
    """Notify users with notifications-consumables right that the consumables of an equipment are expiring.

    Args:
        request (pyramid.request.Request).
        tenant_id (str).
        assets (list[asset_tracker.models.Asset]).
        expiration_date (date): consumable expiration date (YYYY-MM-DD).
        delay_days (int): number of days before expiration.
    """
    template_data = {
        'app_url': request.registry.tenant_config.get_for_tenant('asset_tracker.server_url', tenant_id),
        'assets': assets,
        'cloud_name': request.registry.settings['asset_tracker.cloud_name'],
        'delay_days': delay_days,
        'expiration_date': expiration_date,
    }

    # Email.
    subject = _('Consumables expiration reminder')
    text = 'emails/consumables_expiration.txt'
    html = 'emails/consumables_expiration.html'
    emails = request.notifier.render_emails(subject, text, html, template_data)

    # Asynchronous POST.
    request.notifier.notify({
        'message': {'email': emails},
        'rights': ['notifications-consumables'],
        'tenant': tenant_id,
    })

    request.logger_technical.info(['notify consumables expiration', [asset.id for asset in assets]])
