from collections import OrderedDict
from pathlib import Path

import pkg_resources
from pyramid.i18n import TranslationString as _

ASSET_TRACKER_VERSION = pkg_resources.require(__package__)[0].version
DEFAULT_BRANDING = 'parsys'

STATIC_FILES_CACHE = 60 * 60
USER_INACTIVITY_MAX = 60 * 60

ADMIN_PRINCIPAL = 'g:admin'
CALIBRATION_FREQUENCIES_YEARS = OrderedDict([
    ('default', 2),
    ('maritime', 3),
])
GLUCOMETER_ID = '2YUEMLmH'
SITE_TYPES = [
    _('Company'),
    _('Hospital'),
    _('Nursing home'),
    _('Ship'),
]
WARRANTY_DURATION_YEARS = 2

PATH = Path(__file__).resolve().parent
TEMPLATES_PATH = PATH / 'templates'
TRANSLATIONS_PATH = PATH / 'locale'
