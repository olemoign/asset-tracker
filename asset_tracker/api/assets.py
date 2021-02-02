from datetime import datetime
from json import JSONDecodeError

from parsys_utilities.authorization import authenticate_rta
from parsys_utilities.config import aslist
from pyramid.httpexceptions import HTTPBadRequest, HTTPOk
from pyramid.security import Allow, Everyone
from pyramid.view import view_config
from sentry_sdk import capture_exception, capture_message
from sqlalchemy.exc import SQLAlchemyError

from asset_tracker import models
from asset_tracker.constants import CALIBRATION_FREQUENCIES_YEARS
from asset_tracker.views.assets import Assets as AssetView


class Assets:
    def __acl__(self):
        # Authenticate RTA using HTTP Basic Auth.
        if authenticate_rta(self.request):
            return [
                (Allow, None, Everyone, 'api-assets-site'),
            ]
        else:
            return []

    def __init__(self, request):
        self.request = request

    def link_asset(self, json):
        """Create/Update an asset based on information from RTA.
        Find and update asset information if asset exists in AssetTracker or create it.

        Args:
            json (dict).
        """
        # Marlink has only one calibration frequency so they don't want to see the input.
        specific = aslist(self.request.registry.settings.get('asset_tracker.specific'))
        if 'marlink' in specific:
            calibration_frequency = CALIBRATION_FREQUENCIES_YEARS['marlink']
        else:
            calibration_frequency = CALIBRATION_FREQUENCIES_YEARS['default']

        # If the asset exists in both the Asset Tracker and RTA.
        asset = self.request.db_session.query(models.Asset).filter_by(user_id=json['userID']).first()

        if asset:
            self.update_asset(asset, json)
            return

        # If the asset only exists in the Asset Tracker.
        asset = self.request.db_session.query(models.Asset).filter_by(asset_id=json['login']).first()

        if asset:
            if asset.user_id:
                capture_message(
                    f'Trying to link asset {asset.id} which is already linked: {asset.user_id}/{json["userID"]}.'
                )
                return

            self.update_asset(asset, json)
            return

        # New Asset.
        status = self.request.db_session.query(models.EventStatus).filter_by(status_id='stock_parsys').first()

        asset = models.Asset(
            asset_type='station',
            asset_id=json['login'],
            user_id=json['userID'],
            tenant_id=json['tenantID'],
            calibration_frequency=calibration_frequency,
        )
        self.request.db_session.add(asset)

        # Add Event
        event = models.Event(
            status=status,
            date=datetime.utcnow().date(),
            creator_id=json['creatorID'],
            creator_alias=json['creatorAlias'],
        )
        # noinspection PyProtectedMember
        asset._history.append(event)
        self.request.db_session.add(event)

        # Update status and calibration
        AssetView.update_status_and_calibration_next(asset)

    def update_asset(self, asset, json):
        """Update asset.

        Args:
            asset (rta.models.Asset).
            json (dict).
        """
        if asset.tenant_id != json['tenantID'] and json['tenantType'] != 'Test':
            event = models.Event(
                date=datetime.utcnow().date(),
                creator_id=json['creatorID'],
                creator_alias=json['creatorAlias'],
                status=self.request.db_session.query(models.EventStatus).filter_by(status_id='site_change').first(),
            )
            # noinspection PyProtectedMember
            asset._history.append(event)
            self.request.db_session.add(event)

            # As an asset and its site must have the same tenant, if the asset's tenant changed, its site cannot
            # be valid anymore.
            asset.site_id = None

        asset.user_id = json['userID']
        asset.asset_id = json['login']
        asset.tenant_id = json['tenantID']

    def rta_link_post(self):
        """/api/assets/ POST view. The route is also used in api.datatables but it's more logical to have this code
        here."""
        # Make sure the JSON provided is valid.
        try:
            json = self.request.json
        except JSONDecodeError as error:
            self.request.logger_technical.info('Asset linking: invalid JSON.')
            capture_exception(error)
            raise HTTPBadRequest()

        asset_info = {'creatorAlias', 'creatorID', 'login', 'tenantID', 'tenantType', 'userID'}
        # Validate data.
        if any(not json.get(field) for field in asset_info):
            self.request.logger_technical.info('Asset linking: missing values.')
            raise HTTPBadRequest()

        # Create or update Asset.
        try:
            self.link_asset(json)

        except SQLAlchemyError as error:
            self.request.logger_technical.info('Asset linking: db error.')
            capture_exception(error)
            raise HTTPBadRequest()

        else:
            return HTTPOk()

    @view_config(route_name='api-assets-site', request_method='GET', permission='api-assets-site', renderer='json')
    def site_id_get(self):
        user_id = self.request.matchdict.get('user_id')
        asset = self.request.db_session.query(models.Asset).filter_by(user_id=user_id).first()
        return {'site_id': asset.site.site_id if asset and asset.site else None}


def includeme(config):
    config.add_route(pattern=r'assets/{user_id:\w{8}}/site/', name='api-assets-site', factory=Assets)
