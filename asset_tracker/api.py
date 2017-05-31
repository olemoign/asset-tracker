import os
from collections import OrderedDict
from copy import deepcopy

from parsys_utilities.api import manage_datatables_queries
from parsys_utilities.authorization import Right
from parsys_utilities.dates import format_date
from parsys_utilities.sql import sql_search
from pyramid.httpexceptions import HTTPBadRequest, HTTPNotFound
from pyramid.security import Allow
from pyramid.settings import asbool
from pyramid.view import view_config

from asset_tracker import models


class Assets(object):
    __acl__ = [
        (Allow, None, 'assets-list', 'assets-list'),
        (Allow, None, 'g:admin', 'assets-list'),
    ]

    def __init__(self, request):
        self.request = request

    def apply_tenanting_filter(self, q):
        if 'g:admin' in self.request.effective_principals:
            return q
        else:
            authorized_tenants = {right.tenant for right in self.request.effective_principals
                                  if isinstance(right, Right) and right.name == 'assets-list'}
            return q.filter(models.Asset.tenant_id.in_(authorized_tenants))

    @view_config(route_name='api-assets', request_method='GET', permission='assets-list', renderer='json')
    def list_get(self):
        if not asbool(self.request.GET.get('datatables')):
            return []

        try:
            draw, limit, offset, search, sort, full_text_search = manage_datatables_queries(self.request.GET)
        except KeyError:
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
            return HTTPBadRequest()

        assets = []
        for asset in output['items']:
            if asset.calibration_next:
                calibration_next = format_date(asset.calibration_next, self.request.locale_name)
            else:
                calibration_next = None

            asset_type = self.request.localizer.translate(asset.asset_type.capitalize())
            status = self.request.localizer.translate(asset.status.label)

            asset_output = {'id': asset.id, 'asset_id': asset.asset_id, 'asset_type': asset_type,
                            'customer_name': asset.customer_name, 'site': asset.site, 'status': status,
                            'calibration_next': calibration_next}

            has_admin_rights = 'g:admin' in self.request.effective_principals
            has_read_rights = (asset.tenant_id, 'assets-read') in self.request.effective_principals
            if has_admin_rights or has_read_rights:
                link = self.request.route_path('assets-update', asset_id=asset.id)
                asset_output['links'] = [{'rel': 'self', 'href': link}]

            assets.append(asset_output)

        return {'draw': draw, 'recordsTotal': output.get('recordsTotal'), 'recordsFiltered': output['recordsFiltered'],
                'data': assets}


class Software(object):
    __acl__ = [
        (Allow, None, 'software-update', 'software-update'),
        (Allow, None, 'g:admin', 'software-update'),
    ]

    def __init__(self, request):
        self.request = request
        self.product = None

    def get_version_from_file(self, file_name):
        # Remove file extension
        file_name = os.path.splitext(file_name)[0]
        file_name = file_name.lstrip(self.product)
        file_name = file_name.lstrip('-')
        return file_name

    @view_config(route_name='api-software-update', request_method='GET', permission='software-update', renderer='json')
    def software_update_get(self):
        self.product = self.request.GET.get('product')
        if not self.product:
            return HTTPBadRequest(json={'error': 'Missing product.'})

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
            version = self.get_version_from_file(product_file)
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
        channel_versions = deepcopy(product_versions)

        channel = self.request.GET.get('channel', 'stable')
        if channel not in ['alpha', 'beta', 'dev', 'rc']:
            for version, file in product_versions.items():
                if 'alpha' in version or 'beta' in version:
                    channel_versions.pop(version)

        channel_version = channel_versions.popitem(last=True)
        download_url = self.request.route_url('api-software-download', product=self.product, file=channel_version[1])
        return {'version': channel_version[0], 'url': download_url}


def includeme(config):
    config.add_route(pattern='assets/', name='api-assets', factory=Assets)
    config.add_route(pattern='download/{product}/{file}', name='api-software-download')
    config.add_route(pattern='update/', name='api-software-update', factory=Software)
