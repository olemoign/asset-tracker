import logging
import os

from pyramid.i18n import TranslationString as _
from pyramid.settings import asbool

from parsys_utilities.notifications import emails_renderer_offline, notify_offline

FILE_PATH = os.path.dirname(os.path.realpath(__file__))
TEMPLATES_PATH = os.path.join(FILE_PATH, 'templates')
TRANSLATIONS_PATH = os.path.join(FILE_PATH, 'locale')


def next_calibration_notification(ini_configuration, tenant_id, assets, calibration_date):
    """Notify 'HR officer's of an employee's tenant that her/his vocational certificate is expiring.

    Args:
        ini_configuration (dict) asset tracker configuration.
        tenant_id (str).
        assets (list(asset_tracker.models.Asset)).
        calibration_date (str): precise calibration date (YYYY-MM-DD).

    """
    app_name = ini_configuration['asset_tracker.cloud_name']
    subject = _('${app_name} - Device calibration reminder', mapping={'app_name': app_name})
    text = 'emails/calibration_reminder.txt'
    html = 'emails/calibration_reminder.html'

    # Because we are in offline, we have to build the URLs by hand ... This is brittle, it would be nice to do this in
    # a better way.
    assets_url = '{server_url}/assets'.format(server_url=ini_configuration['asset_tracker.server_url'])

    template_data = {
        'app_name': app_name,
        'calibration_date': calibration_date,
        'assets': assets,
        'assets_url': assets_url
    }

    # Template generation
    configuration = {'templates_path': TEMPLATES_PATH, 'translations_path': TRANSLATIONS_PATH}
    emails = emails_renderer_offline(subject, text, html, template_data, **configuration)
    messages = {'email': emails}

    # rights to identify users to prevent for future asset calibration
    rights = ['notifications-calibration']

    # Asynchronous POST
    send_notifications = not asbool(ini_configuration.get('asset_tracker.dev.disable_notifications', False))
    notify_offline(ini_configuration, send_notifications,
                   message=messages, tenant=tenant_id, rights=rights, level='info')

    logging_info = ['notify the assets owner for the next calibration date', [asset.id for asset in assets]]
    logging.getLogger('asset_tracker_technical').info(logging_info)
