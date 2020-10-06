from parsys_utilities.tests import FunctionalTestBase

import asset_tracker
from asset_tracker.constants import PATH


class FunctionalTest(FunctionalTestBase):
    module = asset_tracker
    root = PATH.parent
    set_up_blob_dir = True
