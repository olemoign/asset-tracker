"""Asset tracker API.

List assets for dataTables and asset update WS (declare software version/get last software version).

"""
import os
import re
from collections import OrderedDict
from datetime import datetime
from json import dumps, JSONDecodeError

from parsys_utilities.api import manage_datatables_queries
from parsys_utilities.authorization import Right
from parsys_utilities.dates import format_date
from parsys_utilities.sentry import sentry_exception
from parsys_utilities.sql import sql_search, table_from_dict
from pyramid.authentication import extract_http_basic_credentials
from pyramid.httpexceptions import HTTPBadRequest, HTTPForbidden, HTTPInternalServerError, HTTPNotFound, HTTPOk
from pyramid.security import Allow
from pyramid.settings import asbool, aslist
from pyramid.view import view_config
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound

from asset_tracker import models
from asset_tracker.constants import CALIBRATION_FREQUENCIES_YEARS
from asset_tracker.views_asset import AssetsEndPoint


def get_version_from_file(file_name):
    """Get software version from file name.

    Args:
        file_name (str): file name.

    Returns:
        str: software version.

    """
    # Remove file extension
    file_name = os.path.splitext(file_name)[0]
    return re.search('[0-9]+\.[0-9]+\.[0-9]+.*', file_name).group()


class Assets(object):
    """List assets for dataTables."""
    __acl__ = [
        (Allow, None, 'assets-list', 'assets-list'),
        (Allow, None, 'g:admin', 'assets-list'),
    ]

    def __init__(self, request):
        self.request = request

    def apply_tenanting_filter(self, q):
        """Filter assets according to user's rights/tenants.
        Admins get access to all assets.

        Args:
            q (sqlalchemy.orm.query.Query): current query.

        Returns:
            sqlalchemy.orm.query.Query: filtered query.

        """
        if 'g:admin' in self.request.effective_principals:
            return q
        else:
            authorized_tenants = {right.tenant for right in self.request.effective_principals
                                  if isinstance(right, Right) and right.name == 'assets-list'}
            return q.filter(models.Asset.tenant_id.in_(authorized_tenants))

    @view_config(route_name='api-assets', request_method='GET', permission='assets-list', renderer='json')
    def list_get(self):
        """List assets and format output according to dataTables requirements."""
        # Return if API is called by somebody other than dataTables.
        if not asbool(self.request.GET.get('datatables')):
            return []

        try:
            draw, limit, offset, search, sort, full_text_search = manage_datatables_queries(self.request.GET)
        except KeyError:
            sentry_exception(self.request, level='info')
            return HTTPBadRequest()

        # Simulate the user's tenants as a table so that we can filter/sort on tenant_name.
        tenants = table_from_dict('tenant', self.request.user.tenants)

        search_parameters = {'limit': limit, 'offset': offset, 'search': search, 'sort': sort,
                             'full_text_search': full_text_search}
        full_text_search_attributes = [models.Asset.asset_id, tenants.c.tenant_name, models.Asset.customer_name,
                                       models.Asset.current_location, models.Site.name]
        joined_tables = [(tenants, tenants.c.tenant_id == models.Asset.tenant_id), models.EventStatus, models.Site]
        specific_search_attributes = {'tenant_name': tenants.c.tenant_name, 'status': models.EventStatus.status_id,
                                      'site': models.Site.name}
        specific_sort_attributes = {'tenant_name': tenants.c.tenant_name, 'status': models.EventStatus.position,
                                    'site': models.Site.name}

        try:
            # noinspection PyTypeChecker
            output = sql_search(self.request.db_session, models.Asset, full_text_search_attributes,
                                joined_tables=joined_tables, tenanting=self.apply_tenanting_filter,
                                specific_search_attributes=specific_search_attributes,
                                specific_sort_attributes=specific_sort_attributes, search_parameters=search_parameters)
        except KeyError:
            sentry_exception(self.request, get_tb=True, level='info')
            return HTTPBadRequest()

        tenant_names = {tenant['id']: tenant['name'] for tenant in self.request.user.tenants}

        # Format db return for dataTables.
        assets = []
        for asset in output['items']:
            if asset.calibration_next:
                calibration_next = format_date(asset.calibration_next, self.request.locale_name)
            else:
                calibration_next = None

            status = self.request.localizer.translate(asset.status.label)
            is_active = asset.status.status_id != 'decommissioned'

            asset_output = {
                'id': asset.id,
                'asset_id': asset.asset_id,
                'tenant_name': tenant_names[asset.tenant_id],
                'customer_name': asset.customer_name,
                'site': asset.site.name if asset.site else None,
                'status': status,
                'calibration_next': calibration_next,
                'is_active': is_active
            }

            # Append link to output if the user is an admin or has the right to read the asset info.
            has_admin_rights = 'g:admin' in self.request.effective_principals
            has_read_rights = (asset.tenant_id, 'assets-read') in self.request.effective_principals
            if has_admin_rights or has_read_rights:
                link = self.request.route_path('assets-update', asset_id=asset.id)
                asset_output['links'] = [{'rel': 'self', 'href': link}]

            assets.append(asset_output)

        return {'draw': draw, 'recordsTotal': output.get('recordsTotal'), 'recordsFiltered': output['recordsFiltered'],
                'data': assets}

    def authenticate_rta(self):
        """Authenticate RTA using "reversed" authentication: the asset tracker has credentials to authenticate on RTA
        (client_id/secret). Make RTA use those same credentials to link assets.

        """
        rta_auth = extract_http_basic_credentials(self.request)
        if not rta_auth:
            return False

        client_id = self.request.registry.settings['rta.client_id']
        secret = self.request.registry.settings['rta.secret']

        return client_id == rta_auth.username and secret == rta_auth.password

    def link_asset(self, user_id, login, tenant_id, creator_id, creator_alias):
        """Create/Update an asset based on information from RTA.
        Find and update asset information if asset exists in AssetTracker or create it.

        Args:
            user_id (str): unique id to identify the station
            login (str): serial number or station login/ID
            tenant_id (str): unique id to identify the tenant
            creator_id (str): unique id to identify the user
            creator_alias (str): '{first_name} {last_name}'

        Returns:
            flash (dict): information to be displayed in RTA session.flash

        """
        # IF asset exists in both Asset Tracker and RTA...
        asset = self.request.db_session.query(models.Asset) \
            .filter_by(user_id=user_id) \
            .first()

        if asset:
            if asset.asset_id != login:
                asset.asset_id = login

            if asset.tenant_id != tenant_id:
                asset.tenant_id = tenant_id
                # As an asset and its site must have the same tenant, if the asset's tenant changed, its site cannot
                # be valid anymore.
                asset.site_id = None

            return

        # ...ELSE IF asset exists only in Asset Tracker...
        asset = self.request.db_session.query(models.Asset) \
            .filter_by(asset_id=login, user_id=None) \
            .first()

        if asset:
            asset.user_id = user_id

            if asset.tenant_id != tenant_id:
                asset.tenant_id = tenant_id
                # As an asset and its site must have the same tenant, if the asset's tenant changed, its site cannot
                # be valid anymore.
                asset.site_id = None

            return

        # ...ELSE create a new Asset
        # status selection for new Asset
        status = self.request.db_session.query(models.EventStatus) \
            .filter_by(status_id='stock_parsys') \
            .one()

        # Marlink has only one calibration frequency so they don't want to see the input.
        client_specific = aslist(self.request.registry.settings.get('asset_tracker.client_specific', []))
        if 'marlink' in client_specific:
            calibration_frequency = CALIBRATION_FREQUENCIES_YEARS['maritime']
        else:
            calibration_frequency = 2

        # noinspection PyArgumentList
        asset = models.Asset(asset_type='station', asset_id=login, user_id=user_id, tenant_id=tenant_id,
                             calibration_frequency=calibration_frequency)
        self.request.db_session.add(asset)

        # Add Event
        # noinspection PyArgumentList
        event = models.Event(status=status, date=datetime.utcnow().date(),
                             creator_id=creator_id, creator_alias=creator_alias)
        # noinspection PyProtectedMember
        asset._history.append(event)
        self.request.db_session.add(event)

        # Update status and calibration
        AssetsEndPoint.update_status_and_calibration_next(asset, client_specific)

    @view_config(route_name='api-assets', request_method='POST', require_csrf=False)
    def rta_link_post(self):
        """Link Station (RTA) and Asset (AssetTracker).
        Receive information from RTA about station to create/update Asset.

        """
        # Authentify RTA using HTTP Basic Auth.
        if not self.authenticate_rta():
            return HTTPForbidden()

        # Make sure the JSON provided is valid.
        try:
            json = self.request.json

        except JSONDecodeError:
            self.request.logger_technical.info('Asset linking: invalid JSON.')
            sentry_exception(self.request, level='info')
            return HTTPBadRequest()

        else:
            asset_keys = ('userId', 'logIn', 'tenantId', 'creatorID', 'creatorAlias')
            data = {k: json.get(k) for k in asset_keys}

        # Check information availability
        if not all(data.values()):
            self.request.logger_technical.info('Asset linking: missing values.')
            return HTTPBadRequest()

        # Create or update Asset
        try:
            self.link_asset(data['userId'], data['logIn'], data['tenantId'], data['creatorID'], data['creatorAlias'])

        except SQLAlchemyError:
            self.request.logger_technical.info('Asset linking: db error.')
            sentry_exception(self.request, level='info')
            return HTTPBadRequest()

        else:
            return HTTPOk()


class Sites(object):
    """List sites for dataTables."""
    # 'external-sites-read' permission is exceptionally controlled in site_get() method.
    __acl__ = [
        (Allow, None, 'sites-list', 'sites-list'),
        (Allow, None, 'g:admin', 'sites-list'),
    ]

    def __init__(self, request):
        self.request = request
        self.asset = self.get_asset()

    def get_asset(self):
        user_id = self.request.matchdict.get('user_id')
        if not user_id:
            return

        # if asset is missing, site_get() method will return an empty response
        asset = self.request.db_session.query(models.Asset) \
            .filter_by(user_id=user_id) \
            .options(joinedload('site')) \
            .first()

        return asset

    def apply_tenanting_filter(self, q):
        """Filter sites according to user's rights/tenants.
        Admins get access to all sites.

        Args:
            q (sqlalchemy.orm.query.Query): current query.

        Returns:
            sqlalchemy.orm.query.Query: filtered query.

        """
        if 'g:admin' in self.request.effective_principals:
            return q
        else:
            authorized_tenants = {right.tenant for right in self.request.effective_principals
                                  if isinstance(right, Right) and right.name == 'sites-list'}
            return q.filter(models.Site.tenant_id.in_(authorized_tenants))

    @view_config(route_name='api-sites', request_method='GET', permission='sites-list', renderer='json')
    def list_get(self):
        """List sites and format output according to dataTables requirements."""
        # Return if API is called by somebody other than dataTables.
        if not asbool(self.request.GET.get('datatables')):
            return []

        # Parse data from datatables
        try:
            draw, limit, offset, search, sort, full_text_search = manage_datatables_queries(self.request.GET)
        except KeyError:
            sentry_exception(self.request, level='info')
            return HTTPBadRequest()

        # Simulate the user's tenants as a table so that we can filter/sort on tenant_name.
        tenants = table_from_dict('tenant', self.request.user.tenants)

        # SQL query parameters
        full_text_search_attributes = [models.Site.name, models.Site.site_type, tenants.c.tenant_name,
                                       models.Site.contact, models.Site.phone, models.Site.email]
        joined_tables = [(tenants, tenants.c.tenant_id == models.Site.tenant_id)]
        specific_search_attributes = {'tenant_name': tenants.c.tenant_name}
        specific_sort_attributes = {'tenant_name': tenants.c.tenant_name}
        search_parameters = {'limit': limit, 'offset': offset, 'search': search, 'sort': sort,
                             'full_text_search': full_text_search}
        try:
            # noinspection PyTypeChecker
            output = sql_search(db_session=self.request.db_session,
                                searched_object=models.Site,
                                full_text_search_attributes=full_text_search_attributes,
                                joined_tables=joined_tables,
                                tenanting=self.apply_tenanting_filter,
                                specific_search_attributes=specific_search_attributes,
                                specific_sort_attributes=specific_sort_attributes,
                                search_parameters=search_parameters)
        except KeyError:
            sentry_exception(self.request, get_tb=True, level='info')
            return HTTPBadRequest()

        # dict to get tenant name from tenant id
        tenant_names = {tenant['id']: tenant['name'] for tenant in self.request.user.tenants}

        # Format db return for dataTables.
        sites = []
        for site in output['items']:
            site_type = None
            if site.site_type:
                site_type = self.request.localizer.translate(site.site_type)

            site_output = {
                'name': site.name,
                'site_type': site_type,
                'tenant_name': tenant_names[site.tenant_id],
                'contact': site.contact,
                'phone': site.phone,
                'email': site.email,
            }

            # Append link to output if the user is an admin or has the right to read the site info.
            has_admin_rights = 'g:admin' in self.request.effective_principals
            has_read_rights = (site.tenant_id, 'sites-read') in self.request.effective_principals

            if has_admin_rights or has_read_rights:
                link = self.request.route_path('sites-update', site_id=site.id)
                site_output['links'] = [{'rel': 'self', 'href': link}]

            sites.append(site_output)

        return {
            'draw': draw,
            'recordsTotal': output.get('recordsTotal'),
            'recordsFiltered': output['recordsFiltered'],
            'data': sites
        }

    @view_config(route_name='api-sites-information', request_method='GET', renderer='sites-information.html')
    def site_get(self):
        """Get site information for consultation.

        Html response to insert directly into the consultation. Permissions are exceptionally controlled in the method,
        so that there always is a response, even if the asset or the site doesn't exist. This means that the iframe
        will always send the postMessage to give its size.

        """
        if not self.asset or not self.asset.site:
            return {}

        try:
            # Check permission
            if (self.asset.tenant_id, 'api-sites-read') not in self.request.effective_principals:
                tenant_id = self.asset.tenant_id
                principals = self.request.effective_principals
                print(tenant_id, principals)
                raise HTTPForbidden()

        except HTTPForbidden:
            sentry_exception(self.request)
            return {}

        site_information = self.asset.site
        return {
            'name': site_information.name,
            'site_type': site_information.site_type,
            'contact': site_information.contact,
            'phone': site_information.phone,
            'email': site_information.email,
        }


class Software(object):
    """Software update WebServices: tell to the assets what is the latest version and url of a given product +
    store what software versions a given asset is using.

    """
    __acl__ = [
        (Allow, None, 'api-software-update', 'api-software-update'),
        (Allow, None, 'g:admin', 'api-software-update'),
    ]

    def __init__(self, request):
        self.request = request
        self.product = None

    @view_config(route_name='api-software-update', request_method='GET', permission='api-software-update',
                 renderer='json')
    def software_update_get(self):
        """Return what is the lastest version of a product in a given branch (alpha/beta/dev/stable) and the url
        where to download the package.

        QueryString:
            product (mandatory).
            channel (optional): product channel (in 'alpha', 'beta', 'dev', 'stable').
            version (optional): if we want the url of one specific version.

        """
        product = self.request.GET.get('product')
        if not product:
            return HTTPBadRequest(json={'error': 'Missing product.'})
        else:
            self.product = product.lower()

        # If storage folder wasn't set up, can't return link.
        storage = self.request.registry.settings.get('asset_tracker.software_storage')
        if not storage:
            return {}

        # Products are stored in sub-folders in the storage path.
        # As os.walk is recursive, we need to work the results a bit.
        products = next(os.walk(storage), [])
        products = products[1] if products else []
        if self.product not in products:
            return HTTPNotFound(json={'error': 'Unknown product.'})

        product_folder = os.path.join(storage, self.product)
        product_files = next(os.walk(product_folder))[2]

        product_versions = {}
        for product_file in product_files:
            version = get_version_from_file(product_file)
            product_versions[version] = product_file
        # Sort dictionary by version (which are the keys of the dict).
        product_versions = OrderedDict(sorted(product_versions.items(), key=lambda k: k[0]))

        version = self.request.GET.get('version')
        if version and version in product_versions.keys():
            file = product_versions[version]
            download_url = self.request.route_url('api-software-download', product=self.product, file=file)
            return {'version': version, 'url': download_url}
        elif version:
            return {}

        # Create a new OrderedDict for the output so that we can mutate the dict while looping on it.
        channel_versions = OrderedDict()

        channel = self.request.GET.get('channel', 'stable')
        for version, file in product_versions.items():
            alpha = 'alpha' in version and channel in ['alpha', 'dev']
            beta = 'beta' in version and channel in ['beta', 'alpha', 'dev']
            stable = 'alpha' not in version and 'beta' not in version
            if alpha or beta or stable:
                channel_versions[version] = file

        # If no version was found for the requested parameters.
        if not channel_versions:
            return {}

        # We return only the latest version.
        channel_version = channel_versions.popitem(last=True)
        download_url = self.request.route_url('api-software-download', product=self.product, file=channel_version[1])
        return OrderedDict(version=channel_version[0], url=download_url)

    @view_config(route_name='api-software-update', request_method='POST', permission='api-software-update',
                 require_csrf=False, renderer='json')
    def software_update_post(self):
        """Receive software(s) version.

        QueryString:
            product (mandatory).

        Body (json):
            version (mandatory).
            position (optional).

        """
        # get product name (medcapture, camagent)
        if not self.request.GET.get('product'):
            return HTTPBadRequest(json={'error': 'Missing product.'})
        else:
            self.product = self.request.GET['product'].lower()

        # make sure the JSON provided is valid.
        try:
            json = self.request.json
        except JSONDecodeError:
            sentry_exception(self.request, level='info')
            return HTTPBadRequest(json={'error': 'Invalid JSON.'})

        # check if asset exists (cart, station, telecardia)
        try:
            station_login = self.request.user.login
        except KeyError:
            return HTTPBadRequest(json={'error': 'Invalid authentication.'})

        asset = self.request.db_session.query(models.Asset) \
            .filter_by(asset_id=station_login) \
            .first()
        if not asset:
            return HTTPNotFound(json={'error': 'Unknown asset.'})

        software_version = json.get('version')
        if software_version:
            latest_events = asset.history(order='desc') \
                .join(models.EventStatus).filter(models.EventStatus.status_id == 'software_update')

            last_event_generator = (e for e in latest_events if e.extra_json['software_name'] == self.product)
            last_event = next(last_event_generator, None)

            if not last_event or last_event.extra_json['software_version'] != software_version:
                try:
                    software_status = self.request.db_session.query(models.EventStatus) \
                        .filter(models.EventStatus.status_id == 'software_update').one()
                except (MultipleResultsFound, NoResultFound):
                    sentry_exception(self.request, level='info')
                    self.request.logger_technical.info('asset status error')
                    return HTTPInternalServerError(json={'error': 'Internal server error.'})

                # noinspection PyArgumentList
                new_event = models.Event(
                    status=software_status,
                    date=datetime.utcnow().date(),
                    creator_id=self.request.user.id,
                    creator_alias=self.request.user.alias,
                    extra=dumps({'software_name': self.product,
                                 'software_version': software_version})
                )

                # noinspection PyProtectedMember
                asset._history.append(new_event)

                self.request.db_session.add(new_event)

            return HTTPOk(json='Information received.')

        return HTTPBadRequest(json='Missing software version.')


def includeme(config):
    config.add_route(pattern='assets/', name='api-assets', factory=Assets)
    config.add_route(pattern='assets/{user_id:\w{8}}/site/', name='api-sites-information', factory=Sites)
    config.add_route(pattern='sites/', name='api-sites', factory=Sites)  # for datatables
    config.add_route(pattern='download/{product}/{file}', name='api-software-download')
    config.add_route(pattern='update/', name='api-software-update', factory=Software)
