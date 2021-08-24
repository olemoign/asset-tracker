import logging
from urllib.parse import urljoin

from parsys_utilities.notifications import emails_renderer_offline, notify_offline
from pyramid.i18n import TranslationString as _

from asset_tracker.constants import TEMPLATES_PATH, TRANSLATIONS_PATH

logger = logging.getLogger('asset_tracker_technical')


def consumables_expiration(tenant_config, equipment, expiration_date, delay_days):
    """Notify users with notifications-consumables right that the consumables of an equipment are expiring.

    Args:
        tenant_config (parsys_utilities.config.TenantConfigurator).
        equipment (asset_tracker.models.Equipment)).
        expiration_date (date): consumable expiration date (YYYY-MM-DD).
        delay_days (int): number of days before expiration.
    """
    app_name = tenant_config.settings['app:main']['asset_tracker.cloud_name']
    subject = _('${app_name} - Equipment consumables expiration reminder', mapping={'app_name': app_name})
    text = 'emails/consumables_expiration.txt'
    html = 'emails/consumables_expiration.html'

    expired_consumables = []
    for consumable in equipment.consumables:
        if consumable.expiration_date.strftime('%Y-%m-%d') == expiration_date:
            expired_consumables.append(consumable.family.model)

    server_url = tenant_config.settings['app:main']['asset_tracker.server_url']
    template_data = {
        'app_name': app_name,
        'asset_id': equipment.asset.asset_id,
        'asset_url': urljoin(server_url, f'/assets/{equipment.asset.id}/'),
        'delay_days': delay_days,
        'equipment': equipment.family.model,
        'expired_consumables': expired_consumables,
        'expiration_date': expiration_date,
    }

    # Template generation
    emails = emails_renderer_offline(TEMPLATES_PATH, TRANSLATIONS_PATH, subject, text, html, template_data)
    messages = {'email': emails}

    # Asynchronous POST
    json = {
        'level': 'info',
        'message': messages,
        'rights': ['notifications-consumables'],
        'tenant': equipment.asset.tenant.tenant_id,
    }
    notify_offline(tenant_config, json)

    logger.info(['notify consumables expiration', equipment.id])


def next_calibration(tenant_config, tenant_id, assets, calibration_date):
    """Notify an asset owner that the asset needs to be calibrated.

    Args:
        tenant_config (parsys_utilities.config.TenantConfigurator).
        tenant_id (str).
        assets (list[asset_tracker.models.Asset]).
        calibration_date (date): precise calibration date (YYYY-MM-DD).
    """
    app_name = tenant_config.settings['app:main']['asset_tracker.cloud_name']
    subject = _('${app_name} - Device calibration reminder', mapping={'app_name': app_name})
    text = 'emails/calibration_reminder.txt'
    html = 'emails/calibration_reminder.html'

    # Because we are in offline, we have to build the URLs by hand ... This is brittle, it would be nice to do this in
    # a better way.
    server_url = tenant_config.settings['app:main']['asset_tracker.server_url']
    template_data = {
        'app_name': app_name,
        'assets': assets,
        'assets_url': urljoin(server_url, '/assets/'),
        'calibration_date': calibration_date,
    }

    # Template generation
    emails = emails_renderer_offline(TEMPLATES_PATH, TRANSLATIONS_PATH, subject, text, html, template_data)
    messages = {'email': emails}

    json = {'level': 'info', 'message': messages, 'rights': ['notifications-calibration'], 'tenant': tenant_id}
    notify_offline(tenant_config, json)

    logger.info(['notify calibration date', [asset.id for asset in assets]])
