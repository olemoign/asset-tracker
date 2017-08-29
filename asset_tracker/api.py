"""Asset tracker API

List assets for dataTables and asset update WS (declare software version/get last software version).
"""

import os
import re
from collections import OrderedDict
from datetime import date
from json import dumps, JSONDecodeError

from parsys_utilities.api import manage_datatables_queries
from parsys_utilities.authorization import Right
from parsys_utilities.dates import format_date
from parsys_utilities.sentry import sentry_capture_exception
from parsys_utilities.sql import sql_search
from pyramid.httpexceptions import HTTPBadRequest, HTTPOk, HTTPNotFound
from pyramid.security import Allow
from pyramid.settings import asbool
from pyramid.view import view_config

from asset_tracker import models


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
        Admins get access to all asssets.

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
        # Return if API is called by somebdy other than dataTables.
        if not asbool(self.request.GET.get('datatables')):
            return []

        try:
            draw, limit, offset, search, sort, full_text_search = manage_datatables_queries(self.request.GET)
        except KeyError:
            sentry_capture_exception(self.request, level='info')
            return HTTPBadRequest()

        search_parameters = {'limit': limit, 'offset': offset, 'search': search, 'sort': sort,
                             'full_text_search': full_text_search}
        joined_tables = [models.EventStatus]
        full_text_search_attributes = [models.Asset.asset_id, models.Asset.customer_name, models.Asset.site,
                                       models.Asset.current_location]
        specific_search_attributes = {'status': models.EventStatus.status_id}
        specific_sort_attributes = {'status': models.EventStatus.position}

        try:
            # noinspection PyTypeChecker
            output = sql_search(self.request.db_session, models.Asset, full_text_search_attributes,
                                joined_tables=joined_tables, tenanting=self.apply_tenanting_filter,
                                specific_search_attributes=specific_search_attributes,
                                specific_sort_attributes=specific_sort_attributes, search_parameters=search_parameters)
        except KeyError:
            sentry_capture_exception(self.request, get_tb=True, level='info')
            return HTTPBadRequest()

        # Format db return for dataTables.
        assets = []
        for asset in output['items']:
            if asset.calibration_next:
                calibration_next = format_date(asset.calibration_next, self.request.locale_name)
            else:
                calibration_next = None

            asset_type = self.request.localizer.translate(asset.asset_type.capitalize())
            status = self.request.localizer.translate(asset.status.label)
            is_active = asset.status.status_id != 'decommissioned'

            asset_output = {'id': asset.id, 'asset_id': asset.asset_id, 'asset_type': asset_type,
                            'customer_name': asset.customer_name, 'site': asset.site, 'status': status,
                            'calibration_next': calibration_next, 'is_active': is_active}

            # Append link to output if the user is an admin or has the right to read the asset info.
            has_admin_rights = 'g:admin' in self.request.effective_principals
            has_read_rights = (asset.tenant_id, 'assets-read') in self.request.effective_principals
            if has_admin_rights or has_read_rights:
                link = self.request.route_path('assets-update', asset_id=asset.id)
                asset_output['links'] = [{'rel': 'self', 'href': link}]

            assets.append(asset_output)

        return {'draw': draw, 'recordsTotal': output.get('recordsTotal'), 'recordsFiltered': output['recordsFiltered'],
                'data': assets}


class Software(object):
    """Software update WebServices: tell to the assets what is the latest version and url of a given product +
    store what software versions a given asset is using.

    """
    __acl__ = [
        (Allow, None, 'software-update', 'software-update'),
        (Allow, None, 'g:admin', 'software-update'),
    ]

    def __init__(self, request):
        self.request = request
        self.product = None

    @view_config(route_name='api-software-update', request_method='GET', permission='software-update', renderer='json')
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

    @view_config(route_name='api-software-update', request_method='POST', permission='software-update',
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
        except JSONDecodeError as error:
            return HTTPBadRequest(json={'error': error})

        # check if asset exists (cart, station, telecardia)
        try:
            station_login = self.request.user['login']
        except KeyError:
            return HTTPBadRequest(json={'error': 'Invalid authentication.'})

        asset = self.request.db_session.query(models.Asset) \
            .filter_by(asset_id=station_login) \
            .first()
        if not asset:
            return HTTPNotFound(json={'error': 'Unknown asset.'})

        software_version = json.get('version')
        if software_version:
            latest_events = self.request.db_session.query(models.Event).join(models.EventStatus) \
                .filter(models.Event.asset_id == asset.id,
                        models.EventStatus.status_id == 'software_update') \
                .order_by(models.Event.id.desc())

            last_event_generator = (e for e in latest_events if e.data_json['software_name'] == self.product)
            last_event = next(last_event_generator, None)

            if not last_event or last_event.data_json['software_version'] != software_version:
                # noinspection PyArgumentList
                new_event = models.Event(
                    asset_id=asset.id,
                    date=date.today(),
                    creator_id=self.request.user['id'],
                    creator_alias=self.request.user['alias'],
                    status_id=10,
                    extra=dumps({'software_name': self.product,
                                 'software_version': software_version})
                )
                self.request.db_session.add(new_event)

            return HTTPOk(json='Information received.')

        return HTTPBadRequest(json='No usable information was transmitted.')


def includeme(config):
    config.add_route(pattern='assets/', name='api-assets', factory=Assets)
    config.add_route(pattern='download/{product}/{file}', name='api-software-download')
    config.add_route(pattern='update/', name='api-software-update', factory=Software)
