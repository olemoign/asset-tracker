from collections import OrderedDict
from pathlib import Path

import importlib_metadata
from pyramid.i18n import TranslationString as _

ASSET_TRACKER_VERSION = importlib_metadata.version(__package__)

STATIC_FILES_CACHE = 60 * 60
USER_INACTIVITY_MAX = 60 * 60

ADMIN_PRINCIPAL = 'g:admin'
CALIBRATION_FREQUENCIES_YEARS = OrderedDict([
    ('default', 2),
    ('marlink', 3),
])
SITE_TYPES = [
    _('Company'),
    _('Hospital'),
    _('Nursing home'),
    _('Ship'),
]
WARRANTY_DURATION_YEARS = 2

ASSET_TYPES = [
    {'name': 'backpack', 'label': _('Backpack')},
    {'name': 'cart', 'label': _('Cart')},
    {'name': 'station', 'label': _('Station')},
    {'name': 'telecardia', 'label': _('Telecardia')},
]

PATH = Path(__file__).resolve().parent
TEMPLATES_PATH = PATH / 'templates'
TRANSLATIONS_PATH = PATH / 'locale'
