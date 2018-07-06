import gettext
import logging
import os

from jinja2 import Environment, FileSystemLoader
from pyramid.i18n import make_localizer, TranslationString as _

from parsys_utilities import AVAILABLE_LOCALES, celery_tasks, dates

FILE_PATH = os.path.dirname(os.path.realpath(__file__))
TEMPLATES_PATH = os.path.join(FILE_PATH, 'templates')
TRANSLATIONS_PATH = os.path.join(FILE_PATH, 'locale')


def emails_renderer_offline(subject, text_path, html_path, template_data):
    """Generates emails in all the languages available in this application.

    RTA will choose the language according to the user parameters.

    This function is a modification of emails_renderer().
    It allows us to send notifications from outside the WGSI app, in our case, from a Celery worker.

    Args:
         subject (str): email subject.
         text_path (str): path to message body as plain text.
         html_path (str): path to message body as html.
         template_data (dict).

    Returns:
        messages (dict): {<locale_name>: {'subject': str, 'text': str, 'html': str}}.

    """
    # jinja2 configuration
    env = Environment(
        extensions=['jinja2.ext.i18n', 'jinja2.ext.autoescape', 'jinja2.ext.with_'],
        loader=FileSystemLoader(TEMPLATES_PATH)
    )
    env.filters['format_date'] = dates.format_date  # add custom filter to format date according to locale

    text_template = env.get_template(text_path)
    html_template = env.get_template(html_path)

    rendered_emails = dict()
    for locale in AVAILABLE_LOCALES:
        # translate subject
        pyramid_localizer = make_localizer(current_locale_name=locale, translation_directories=[TRANSLATIONS_PATH])
        rendered_subject = pyramid_localizer.translate(subject)

        # translate template
        template_data['locale'] = locale
        translations = gettext.translation(domain='messages', localedir=TRANSLATIONS_PATH, languages=[locale])
        env.install_gettext_translations(translations, newstyle=True)
        rendered_text = text_template.render(template_data)
        rendered_html = html_template.render(template_data)

        rendered_emails[locale] = {
            'subject': rendered_subject,
            'text': rendered_text,
            'html': rendered_html
        }

    return rendered_emails


def notify_offline(ini_configuration, **json):
    """Send notifications from outside the WGSI app.

    This function is a modification of Notifier.notify() from parsys_utilities.notifications.

    Args:
        ini_configuration (dict) Parsys Cloud parameters.

    Keyword Args:
        message (dict).
        tenant (str).
        profiles (list(str)): user_ids or rights.
        level (str).

    """
    notifications_url = '{server_url}/api/notifications/'.format(server_url=ini_configuration['rta.server_url'])
    client_id = ini_configuration['rta.client_id']
    secret = ini_configuration['rta.secret']

    args = [notifications_url, json, client_id, secret]
    celery_tasks.post_json.apply_async(args=args)


def next_calibration_notification(ini_configuration, tenant_id, assets, validity_months, expiration_date):
    """Notify 'HR officer's of an employee's tenant that her/his vocational certificate is expiring.

    Args:
        ini_configuration (dict) asset tracker configuration.
        tenant_id (str).
        assets (list(asset_tracker.models.Asset)).
        validity_months (int): reminder period.
        expiration_date (str): precise expiration date (YYYY-MM-DD).

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
        'expiration_date': expiration_date,
        'validity_months': validity_months,
        'assets': assets,
        'assets_url': assets_url
    }

    # Template generation
    emails = emails_renderer_offline(subject=subject, text_path=text, html_path=html, template_data=template_data)
    messages = {'email': emails}

    assets_ids = [asset.id for asset in assets]

    # Asynchronous POST
    notify_offline(ini_configuration, message=messages, tenant=tenant_id, user_ids=assets_ids, level='info')

    logging_info = ['notify the assets owner for the next calibration date', assets_ids]
    logging.getLogger('asset_tracker_technical').info(logging_info)
