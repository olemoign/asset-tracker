import importlib.metadata
from pathlib import Path

from pyramid.i18n import TranslationString as _

ASSET_TRACKER_VERSION = importlib.metadata.version(__package__)

PATH = Path(__file__).resolve().parent
LOCALES_PATH = [PATH / 'locale']

ASSET_TYPES = {
    'backpack': _('Backpack'),
    'cart': _('Cart'),
    'consumables_case': _('Consumables case'),
    'station': _('Station'),
    'telecardia': _('Telecardia'),
}
CALIBRATION_FREQUENCIES_YEARS = {
    'default': 2,
    'marlink': 4,
}
SITE_TYPES = [
    _('Company'),
    _('Hospital'),
    _('Nursing home'),
    _('Ship'),
]
WARRANTY_DURATION_YEARS = 2
