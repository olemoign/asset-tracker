from re import findall

from pyramid.httpexceptions import HTTPBadRequest
from pyramid.i18n import TranslationString as _
from pyramid.security import Allow
from pyramid.settings import asbool
from pyramid.view import view_config
from sqlalchemy.exc import InvalidRequestError

from . import models
from .utilities.authorization import Right
from .utilities.domain_model import asc, Boolean, desc, func, or_, String


class APIBadRequest(Exception):
    pass


class APIEndPoint(object):
    def __init__(self, request):
        self.request = request

    def manage_api_queries(self):
        # Manage "classic" API query.
        limit = self.request.GET.get('limit')
        offset = self.request.GET.get('offset')
        sort = [q for q in self.request.GET.get('_sort').split(',')] if self.request.GET.get('_sort') else None
        full_text_search = self.request.GET.get('_q')
        search = [(q[0], q[1]) for q in self.request.GET.items() if q[0] not in ('limit', 'offset', '_sort', '_q')]

        if (limit and not limit.isdigit()) or (offset and not offset.isdigit()):
            raise HTTPBadRequest()

        return limit, offset, search, sort, full_text_search

    def manage_datatables_queries(self):
        # Manage datatables queries.
        # Draw is a datables variable that needs to be returned in the response.
        draw = int(self.request.GET.get('draw'))
        offset = self.request.GET.get('start')
        limit = self.request.GET.get('length')

        if not draw or not offset or not limit:
            raise HTTPBadRequest()

        full_text_search = self.request.GET.get('search[value]')

        search = []
        search_qs = self.request.GET.get('search')
        if search_qs:
            params = search_qs.split('==')
            if len(params) == 2:
                search = [(params[0], params[1])]
            else:
                raise HTTPBadRequest()

        # To define the query order, Datatables sends order[sort_order][column] = column_number and
        # order[sort_order][dir] = 'asc' or 'desc'. So we loop through the different keys and format the data according
        # to our needs. (Attribute names are sent in columns[column_number][data]).
        sort = []
        i = 0
        while self.request.GET.get('order[' + str(i) + '][column]'):
            column = str(self.request.GET.get('order[' + str(i) + '][column]'))
            attribute = self.request.GET.get('columns[' + column + '][data]')
            direction = '-' if self.request.GET.get('order[' + str(i) + '][dir]') == 'desc' else ''
            sort.append(direction + attribute)
            i += 1

        return draw, limit, offset, search, sort, full_text_search

    def sql_search(self, searched_object, full_text_search_attributes, joined_tables=None, tenanting=None,
                   specific_sort_attributes=None, search_parameters=None):
        specific_sort_attributes = specific_sort_attributes or []
        search_parameters = search_parameters or {}

        output = {}

        q = self.request.db_session.query(searched_object)
        for table in joined_tables or []:
            q = q.outerjoin(table)

        if tenanting:
            q = tenanting(q)

        output.update({'recordsTotal': q.count()})

        for sort_element in search_parameters.get('sort') or []:
            if sort_element.startswith('-'):
                sort_function = desc
                sort_element = sort_element.lstrip('-')
            else:
                sort_function = asc

            if sort_element in specific_sort_attributes:
                q = q.order_by(sort_function(specific_sort_attributes[sort_element]))
            elif hasattr(searched_object, sort_element):
                attribute = getattr(searched_object, sort_element)
                try:
                    if type(attribute.type) == String:
                        q = q.order_by(sort_function(func.lower(attribute)))
                    else:
                        q = q.order_by(sort_function(attribute))
                except InvalidRequestError:
                    q = q.order_by(sort_function(attribute))
            else:
                raise APIBadRequest(_('Unknown attribute: {}.'.format(sort_element)))

        for search_element in search_parameters.get('search') or []:
            if hasattr(searched_object, search_element[0]):
                attribute = getattr(searched_object, search_element[0])
                search_variable = search_element[1]
                try:
                    if type(attribute.type) == Boolean:
                        search_variable = asbool(search_element[1])
                except InvalidRequestError:
                    pass
                q = q.filter(attribute == search_variable)
            else:
                return APIBadRequest(_('Unknown attribute: {}.'.format(search_element[0])))

        if search_parameters.get('full_text_search'):
            words = findall(r'\w+', search_parameters['full_text_search'])
            for word in words:
                if self.request.db_session.bind.name == 'sqlite':
                    sql_filter = (attribute.ilike('%{}%'.format(word)) for attribute in full_text_search_attributes)
                else:
                    sql_filter = (attribute.match(word) for attribute in full_text_search_attributes)
                q = q.filter(or_(sql_filter))

        output.update({'recordsFiltered': q.count()})

        if search_parameters.get('limit'):
            q = q.limit(search_parameters['limit'])

        if search_parameters.get('offset'):
            q = q.offset(search_parameters['offset'])

        results = q.all()

        output.update({'items': results})
        return output


class Assets(APIEndPoint):
    __acl__ = [
        (Allow, None, 'assets-list', 'assets-list'),
        (Allow, None, 'g:admin', 'assets-list'),
    ]

    def apply_tenanting_filter(self, q):
        if 'g:admin' in self.request.effective_principals:
            return q
        else:
            authorized_tenants = {right.tenant for right in self.request.effective_principals
                                  if isinstance(right, Right) and right.name == 'assets-update'}
            return q.filter(models.Asset.tenant_id.in_(authorized_tenants))

    @view_config(route_name='api-assets', request_method='GET', permission='assets-list', renderer='json')
    def list_get(self):
        if not asbool(self.request.GET.get('datatables')):
            return []

        draw, limit, offset, search, sort, full_text_search = self.manage_datatables_queries()
        search_parameters = {'limit': limit, 'offset': offset, 'search': search, 'sort': sort,
                             'full_text_search': full_text_search}
        full_text_search_attributes = [models.Asset.asset_id, models.Asset.customer_name, models.Asset.site,
                                       models.Asset.current_location]

        # TODO: add tenanting
        output = self.sql_search(models.Asset, full_text_search_attributes, search_parameters=search_parameters)
        # output = self.sql_search(models.Asset, full_text_search_attributes, tenanting=self.apply_tenanting_filter,
        #                          search_parameters=search_parameters)

        assets = []
        for asset in output['items']:
            history = [{'date': str(event.date), 'creator_id': event.creator_id, 'creator_alias': event.creator_alias,
                        'status': event.status} for event in asset.history.order_by(models.Event.date).all()]
            equipments = [{'model': equipment.family.model if equipment.family else None,
                           'serial_number': equipment.serial_number} for equipment in asset.equipments]
            link = None
            if 'g:admin' in self.request.effective_principals or'assets-update' in self.request.effective_principals:
                link = self.request.route_path('assets-update', asset_id=asset.id)
                
            asset_output = {
                'id': asset.id, 'asset_id': asset.asset_id, 'customer_name': asset.customer_name, 'site': asset.site,
                'notes': asset.notes, 'current_location': asset.current_location, 'history': history,
                'next_calibration': str(asset.next_calibration or ''),
                'status': models.Event.status_labels[asset.history.order_by(models.Event.date.desc()).first().status],
                'equipments': equipments, 'links': [{'rel': 'self', 'href': link}]
            }

            assets.append(asset_output)

        return {'draw': draw, 'recordsTotal': output.get('recordsTotal'), 'recordsFiltered': output['recordsFiltered'],
                'data': assets}
    
    
def includeme(config):
    config.add_route(pattern='assets/', name='api-assets', factory=Assets)
