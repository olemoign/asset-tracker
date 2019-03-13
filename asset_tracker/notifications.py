import logging

from parsys_utilities.config import TenantConfigurator
from parsys_utilities.notifications import emails_renderer_offline, notify_offline
from pyramid.i18n import TranslationString as _
from pyramid.settings import asbool

from asset_tracker.configuration import DEFAULT_CONFIG
from asset_tracker.constants import TEMPLATES_PATH, TRANSLATIONS_PATH

logger = logging.getLogger('asset_tracker_technical')


def next_calibration(ini_configuration, tenant_id, assets, calibration_date):
    """Notify 'HR officer's of an employee's tenant that her/his vocational certificate is expiring.

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
