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
CONFIG_STATUS = ['config_update', 'software_update']
GLUCOMETER_ID = '2YUEMLmH'
SITE_TYPES = [
    _('Company'),
    _('Hospital'),
    _('Nursing home'),
    _('Ship'),
]
WARRANTY_DURATION_YEARS = 2

FILE_PATH = Path(__file__).resolve().parent
TEMPLATES_PATH = FILE_PATH / 'templates'
TRANSLATIONS_PATH = FILE_PATH / 'locale'
