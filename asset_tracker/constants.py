from collections import OrderedDict

CALIBRATION_FREQUENCIES_YEARS = OrderedDict([('other', 2), ('maritime', 3)])
GLUCOMETER_ID = '2YUEMLmH'
WARRANTY_DURATION_YEARS = 2


class FormException(Exception):
    """Custom exception to handle form validation of Assets and Sites

    additional parameter (log) indicates if logging is required

    """
    def __init__(self, message, log=False):
        super().__init__(message)
        self.log = log
