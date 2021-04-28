import importlib.metadata
from pathlib import Path

from pyramid.i18n import TranslationString as _

ASSET_TRACKER_VERSION = importlib.metadata.version(__package__)

STATIC_FILES_CACHE = 60 * 60
USER_INACTIVITY_MAX = 60 * 60

ADMIN_PRINCIPAL = 'g:admin'
CALIBRATION_FREQUENCIES_YEARS = {
    'default': 2,
    'marlink': 3,
}
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
    {'name': 'consumables_case', 'label': _('Consumables case')},
    {'name': 'station', 'label': _('Station')},
    {'name': 'telecardia', 'label': _('Telecardia')},
]

PATH = Path(__file__).resolve().parent
TEMPLATES_PATH = PATH / 'templates'
TRANSLATIONS_PATH = PATH / 'locale'
