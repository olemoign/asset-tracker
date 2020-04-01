from datetime import datetime, timezone
from json import JSONDecodeError

from parsys_utilities.authorization import authenticate_rta
from pyramid.httpexceptions import HTTPBadRequest, HTTPForbidden, HTTPOk
from pyramid.settings import aslist
from pyramid.view import view_config
from sentry_sdk import capture_exception, capture_message
from sqlalchemy.exc import SQLAlchemyError

from asset_tracker import models
from asset_tracker.constants import CALIBRATION_FREQUENCIES_YEARS
from asset_tracker.views.assets import Assets as AssetView


class Assets(object):
    def __init__(self, request):
        self.request = request

    def add_site_change_event(self, asset, creator_id, creator_alias):
        status = self.request.db_session.query(models.EventStatus).filter_by(status_id='site_change').one()

        event = models.Event(
            date=datetime.now(timezone.utc).date(),
            creator_id=creator_id,
            creator_alias=creator_alias,
            status=status,
        )
        # noinspection PyProtectedMember
        asset._history.append(event)
        self.request.db_session.add(event)

    def link_asset(self, user_id, login, tenant_id, creator_id, creator_alias):
        """Create/Update an asset based on information from RTA.
        Find and update asset information if asset exists in AssetTracker or create it.

        Args:
            user_id (str): unique id to identify the station
            login (str): serial number or station login/ID
            tenant_id (str): unique id to identify the tenant
            creator_id (str): unique id to identify the user
            creator_alias (str): '{first_name} {last_name}'
        """
        # Marlink has only one calibration frequency so they don't want to see the input.
        specific = aslist(self.request.registry.settings.get('asset_tracker.specific', []))
        if 'marlink' in specific:
            calibration_frequency = CALIBRATION_FREQUENCIES_YEARS['maritime']
        else:
            calibration_frequency = CALIBRATION_FREQUENCIES_YEARS['default']

        # If the asset exists in both the Asset Tracker and RTA.
        asset = self.request.db_session.query(models.Asset).filter_by(user_id=user_id).first()

        if asset:
            if asset.tenant_id != tenant_id:
                if asset.site_id:
                    self.add_site_change_event(asset, creator_id, creator_alias)

                # As an asset and its site must have the same tenant, if the asset's tenant changed, its site cannot
                # be valid anymore.
                asset.site_id = None

            asset.asset_id = login
            asset.tenant_id = tenant_id
            return

        # If the asset only exists in the Asset Tracker.
        asset = self.request.db_session.query(models.Asset).filter_by(asset_id=login).first()

        if asset:
            if asset.user_id:
                capture_message(f'Trying to link asset {asset.id} which is already linked: {asset.user_id}/{user_id}.')
                return

            if asset.tenant_id != tenant_id:
                if asset.site_id:
                    self.add_site_change_event(asset, creator_id, creator_alias)

                # As an asset and its site must have the same tenant, if the asset's tenant changed, its site cannot
                # be valid anymore.
                asset.site_id = None

            asset.tenant_id = tenant_id
            asset.user_id = user_id
            return

        # New Asset.
        status = self.request.db_session.query(models.EventStatus).filter_by(status_id='stock_parsys').one()

        asset = models.Asset(
            asset_type='station',
            asset_id=login,
            user_id=user_id,
            tenant_id=tenant_id,
            calibration_frequency=calibration_frequency,
        )
        self.request.db_session.add(asset)

        # Add Event
        event = models.Event(
            status=status,
            date=datetime.now(timezone.utc).date(),
            creator_id=creator_id,
            creator_alias=creator_alias,
        )
        # noinspection PyProtectedMember
        asset._history.append(event)
        self.request.db_session.add(event)

        # Update status and calibration
        AssetView.update_status_and_calibration_next(asset, specific)

    def rta_link_post(self):
        # Authentify RTA using HTTP Basic Auth.
        if not authenticate_rta(self.request):
            capture_message('Forbidden RTA request.')
            raise HTTPForbidden()

        # Make sure the JSON provided is valid.
        try:
            json = self.request.json
        except JSONDecodeError as error:
            self.request.logger_technical.info('Asset linking: invalid JSON.')
            capture_exception(error)
            raise HTTPBadRequest()

        asset_info = {'creatorAlias', 'creatorID', 'login', 'tenantID', 'userID'}
        # Validate data.
        if any(not json.get(field) for field in asset_info):
            self.request.logger_technical.info('Asset linking: missing values.')
            raise HTTPBadRequest()

        # Create or update Asset.
        try:
            self.link_asset(json['userID'], json['login'], json['tenantID'], json['creatorID'], json['creatorAlias'])
        except SQLAlchemyError as error:
            self.request.logger_technical.info('Asset linking: db error.')
            capture_exception(error)
            raise HTTPBadRequest()

        else:
            return HTTPOk()

    @view_config(route_name='api-assets-site', request_method='GET', renderer='json')
    def site_id_get(self):
        # Authenticate RTA using HTTP Basic Auth.
        if not authenticate_rta(self.request):
            capture_message('Forbidden RTA request.')
            raise HTTPForbidden()

        user_id = self.request.matchdict.get('user_id')
        asset = self.request.db_session.query(models.Asset).filter_by(user_id=user_id).first()
        return {'site_id': asset.site.site_id if asset and asset.site else None}


def includeme(config):
    config.add_route(pattern=r'assets/{user_id:\w{8}}/site/', name='api-assets-site', factory=Assets)
