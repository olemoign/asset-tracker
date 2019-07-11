import logging

from parsys_utilities.config import TenantConfigurator
from parsys_utilities.notifications import emails_renderer_offline, notify_offline
from pyramid.i18n import TranslationString as _
from pyramid.settings import asbool

from asset_tracker.config import DEFAULT_CONFIG
from asset_tracker.constants import TEMPLATES_PATH, TRANSLATIONS_PATH

logger = logging.getLogger('asset_tracker_technical')


def next_calibration(ini_configuration, tenant_id, assets, calibration_date):
    """Notify an asset owner that the asset needs to be calibrated.

    Args:
        ini_configuration (configparser.ConfigParser): asset tracker configuration.
        tenant_id (str).
        assets (list(asset_tracker.models.Asset)).
        calibration_date (str): precise calibration date (YYYY-MM-DD).

    """
    tenant_config = TenantConfigurator(settings=ini_configuration, defaults=DEFAULT_CONFIG)
    app_name = tenant_config.get_for_tenant('asset_tracker.cloud_name', tenant_id)
    subject = _('${app_name} - Device calibration reminder', mapping={'app_name': app_name})
    text = 'emails/calibration_reminder.txt'
    html = 'emails/calibration_reminder.html'

    # Because we are in offline, we have to build the URLs by hand ... This is brittle, it would be nice to do this in
    # a better way.
    assets_url = '{server_url}/assets'.format(server_url=ini_configuration['asset_tracker.server_url'])

    template_data = {
        'app_name': app_name,
        'assets': assets,
        'assets_url': assets_url,
        'calibration_date': calibration_date,
    }

    # Template generation
    emails = emails_renderer_offline(TEMPLATES_PATH, TRANSLATIONS_PATH, subject, text, html, template_data)
    messages = {'email': emails}

    # Asynchronous POST
    disable_notifications = asbool(ini_configuration['app:main'].get('asset_tracker.dev.disable_notifications', False))
    if disable_notifications:
        logger.debug('Notifications are disabled.')
    else:
        json = {'level': 'info', 'message': messages, 'rights': ['notifications-calibration'], 'tenant': tenant_id}
        notify_offline(ini_configuration, json)

    logging_info = ['notify calibration date', [asset.id for asset in assets]]
    logger.info(logging_info)


def consumables_expiration(ini_configuration, equipment, expiration_date, delay_days):
    """Notify users with notifications-consumables right that the consumables of an equipment are expiring.

    Args:
        ini_configuration (configparser.ConfigParser): asset tracker configuration.
        equipment (asset_tracker.models.Equipment)).
        expiration_date (str): consumable expiration date (YYYY-MM-DD).
        delay_days (int): number of days before expiration.
    """
    tenant_id = equipment.asset.tenant_id

    tenant_config = TenantConfigurator(settings=ini_configuration, defaults=DEFAULT_CONFIG)
    app_name = tenant_config.get_for_tenant('asset_tracker.cloud_name', tenant_id)
    subject = _('${app_name} - Equipment consumables expiration reminder', mapping={'app_name': app_name})
    text = 'emails/consumables_expiration.txt'
    html = 'emails/consumables_expiration.html'

    asset_url = '{}/assets/{}'.format(
        ini_configuration['app:main'].get('asset_tracker.server_url'),
        equipment.asset.id,
    )
    model = equipment.family.model.split('-')[0]

    template_data = {
        'app_name': app_name,
        'model': model,
        'asset_id': equipment.asset.asset_id,
        'asset_url': asset_url,
        'expiration_date': expiration_date,
        'delay_days': delay_days,
    }

    # Template generation
    emails = emails_renderer_offline(TEMPLATES_PATH, TRANSLATIONS_PATH, subject, text, html, template_data)
    messages = {'email': emails}

    # Asynchronous POST
    disable_notifications = asbool(ini_configuration['app:main'].get('asset_tracker.dev.disable_notifications', False))
    if disable_notifications:
        logger.debug('Notifications are disabled.')
    else:
        json = {'level': 'info', 'message': messages,
                'rights': ['notifications-consumables'], 'tenant': tenant_id}
        notify_offline(ini_configuration, json)

    logger.info('notify equipment consumables expiration date {}, {}'.format(
        equipment.asset.asset_id, equipment.family.model))
