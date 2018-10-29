import pkg_resources
from collections import OrderedDict

ASSET_TRACKER_VERSION = pkg_resources.require(__package__)[0].version
CALIBRATION_FREQUENCIES_YEARS = OrderedDict([('default', 2), ('maritime', 3)])
DEFAULT_BRANDING = 'parsys'
GLUCOMETER_ID = '2YUEMLmH'
STATIC_FILES_CACHE = 3600
WARRANTY_DURATION_YEARS = 2


class FormException(Exception):
    """Custom exception to handle form validation of Assets and Sites.
    The addditional parameter (log) indicates if logging is required.

    """

    def __init__(self, message, log=False):
        super().__init__(message)
        self.log = log
