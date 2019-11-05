from parsys_utilities.tests import FunctionalTestBase

from asset_tracker.constants import PATH
import asset_tracker


class FunctionalTest(FunctionalTestBase):
    module = asset_tracker
    root = PATH.parent
    set_up_blob_dir = True
