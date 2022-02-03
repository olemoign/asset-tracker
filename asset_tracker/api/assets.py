from datetime import datetime
from json import JSONDecodeError

from parsys_utilities.security.authorization import authenticate_rta
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
        tenant = self.request.db_session.query(models.Tenant).filter_by(tenant_id=json['tenantID']).first()
        if not tenant:
            tenant = models.Tenant(tenant_id=json['tenantID'])
            self.request.db_session.add(tenant)
        tenant.name = json['tenantName']

        # If the asset exists in both the Asset Tracker and RTA.
        asset = self.request.db_session.query(models.Asset).filter_by(user_id=json['userID']) \
            .join(models.Asset.tenant).first()
        if asset:
            self.update_asset(asset, tenant, json)
            return

        # If the asset only exists in the Asset Tracker.
        asset = self.request.db_session.query(models.Asset).filter_by(asset_id=json['login']) \
            .join(models.Asset.tenant).first()
        if asset:
            if asset.user_id:
                capture_message(
                    f'Trying to link asset {asset.id} which is already linked: {asset.user_id}/{json["userID"]}.'
                )
                return

            self.update_asset(asset, tenant, json)
            return

        # Marlink has only one calibration frequency so they don't want to see the input.
        config = self.request.registry.settings.get('asset_tracker.config', 'parsys')
        if config == 'marlink':
            calibration_frequency = CALIBRATION_FREQUENCIES_YEARS['marlink']
        else:
            calibration_frequency = CALIBRATION_FREQUENCIES_YEARS['default']

        # New asset.
        stock_parsys = self.request.db_session.query(models.EventStatus).filter_by(status_id='stock_parsys').one()
        # noinspection PyArgumentList
        asset = models.Asset(
            asset_type='station',
            asset_id=json['login'],
            calibration_frequency=calibration_frequency,
            status=stock_parsys,
            tenant=tenant,
            user_id=json['userID'],
        )
        # Add event.
        # noinspection PyArgumentList
        event = models.Event(
            creator_id=json['creatorID'],
            creator_alias=json['creatorAlias'],
            date=datetime.utcnow().date(),
            status=stock_parsys,
        )
        asset.add_event(event)
        self.request.db_session.add_all([asset, event])

        # Update status and calibration.
        AssetView.update_calibration_next(asset)

    def update_asset(self, asset, tenant, json):
        """Update asset.

        Args:
            asset (rta.models.Asset).
            tenant (rta.models.Tenant).
            json (dict).
        """
        if asset.tenant.tenant_id != json['tenantID'] and json['tenantType'] != 'Test':
            # noinspection PyArgumentList
            event = models.Event(
                creator_id=json['creatorID'],
                creator_alias=json['creatorAlias'],
                date=datetime.utcnow().date(),
                status=self.request.db_session.query(models.EventStatus).filter_by(status_id='site_change').one(),
            )
            asset.add_event(event)
            self.request.db_session.add(event)

            # As an asset and its site must have the same tenant, if the asset's tenant changed, its site cannot
            # be valid anymore.
            asset.site_id = None

        asset.asset_id = json['login']
        asset.tenant = tenant
        asset.user_id = json['userID']

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

        asset_info = {'creatorAlias', 'creatorID', 'login', 'tenantID', 'tenantName', 'tenantType', 'userID'}
        # Validate data.
        if any(not json.get(field) for field in asset_info):
            self.request.logger_technical.info('Asset linking: missing values.')
            capture_message('Asset linking: missing values.')
            raise HTTPBadRequest()

        # Create or update asset.
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
