from parsys_utilities.api import manage_datatables_queries
from parsys_utilities.authorization import Right
from parsys_utilities.dates import format_date
from parsys_utilities.sql import sql_search
from pyramid.httpexceptions import HTTPBadRequest
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
            status, calibration_next = '', ''

            if asset.status:
                status = self.request.localizer.translate(asset.status.label)

            if asset.calibration_next:
                calibration_next = format_date(asset.calibration_next, self.request.locale_name)

            asset_type = self.request.localizer.translate(asset.asset_type.capitalize())

            asset_output = {'id': asset.id, 'asset_id': asset.asset_id, 'asset_type': asset_type,
                            'customer_name': asset.customer_name, 'site': asset.site, 'status': status,
                            'calibration_next': calibration_next}

            has_admin_rights = 'g:admin' in self.request.effective_principals
            has_read_rights = (asset.tenant_id, 'assets-read') in self.request.effective_principals
            if has_admin_rights or has_read_rights:
                link = self.request.route_path('assets-update', asset_id=asset.id)
                asset_output.update({'links': [{'rel': 'self', 'href': link}]})

            assets.append(asset_output)

        return {'draw': draw, 'recordsTotal': output.get('recordsTotal'), 'recordsFiltered': output['recordsFiltered'],
                'data': assets}


def includeme(config):
    config.add_route(pattern='assets/', name='api-assets', factory=Assets)
