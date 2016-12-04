from parsys_utilities.api import manage_datatables_queries
from parsys_utilities.authorization import Right
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
        full_text_search_attributes = [models.Asset.asset_id, models.Asset.customer_name, models.Asset.site,
                                       models.Asset.current_location]
        try:
            output = sql_search(self.request.db_session, models.Asset, full_text_search_attributes,
                                tenanting=self.apply_tenanting_filter, search_parameters=search_parameters)
        except KeyError:
            return HTTPBadRequest()

        assets = []
        for asset in output['items']:
            history = [{'date': str(event.date), 'creator_id': event.creator_id, 'creator_alias': event.creator_alias,
                        'status': event.status} for event in asset.history.order_by(models.Event.date).all()]
            equipments = [{'model': equipment.family.model if equipment.family else None,
                           'serial_number': equipment.serial_number} for equipment in asset.equipments]
            link = None
            if 'g:admin' in self.request.effective_principals or \
                    (asset.tenant_id, 'assets-read') in self.request.effective_principals:
                link = self.request.route_path('assets-update', asset_id=asset.id)

            asset_output = {
                'id': asset.id, 'asset_id': asset.asset_id, 'customer_name': asset.customer_name, 'site': asset.site,
                'notes': asset.notes, 'current_location': asset.current_location, 'history': history,
                'status': models.Event.status_labels[asset.history.order_by(models.Event.date.desc()).first().status],
                'equipments': equipments, 'links': [{'rel': 'self', 'href': link}]
            }

            assets.append(asset_output)

        return {'draw': draw, 'recordsTotal': output.get('recordsTotal'), 'recordsFiltered': output['recordsFiltered'],
                'data': assets}


def includeme(config):
    config.add_route(pattern='assets/', name='api-assets', factory=Assets)
