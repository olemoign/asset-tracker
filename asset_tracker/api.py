from abc import ABCMeta, abstractmethod
from re import findall, UNICODE

from pyramid.httpexceptions import HTTPBadRequest
from pyramid.i18n import TranslationString as _
from pyramid.security import Allow
from pyramid.view import view_config

from .models import Asset, Event
from .utilities.domain_model import func, String


class API(object):
    __metaclass__ = ABCMeta

    def __init__(self, request):
        self.request = request

    @property
    @abstractmethod
    def full_text_search(self):
        return

    @property
    @abstractmethod
    def searched_object(self):
        return

    @property
    @abstractmethod
    def specific_sort_methods(self):
        return

    def manage_api_queries(self):
        limit = self.request.GET.get('limit')
        offset = self.request.GET.get('offset')
        sort = [q for q in self.request.GET.get('_sort').split(',')] if self.request.GET.get('_sort') else None
        full_text_search = self.request.GET.get('_q')
        search = [(q[0], q[1]) for q in self.request.GET.iteritems() if q[0] not in ('limit', 'offset', '_sort', '_q')]

        if (limit and not limit.isdigit()) or (offset and not offset.isdigit()):
            return HTTPBadRequest()

        output = self.search(limit=limit, offset=offset, search=search, sort=sort, full_text_search=full_text_search)
        if output:
            return output
        else:
            return HTTPBadRequest()

    def manage_datatables_queries(self):
        draw = int(self.request.GET.get('draw'))
        offset = self.request.GET.get('start')
        limit = self.request.GET.get('length')
        full_text_search = self.request.GET.get('search[value]')

        sort = []
        i = 0
        while self.request.GET.get('order[' + str(i) + '][column]'):
            column = str(self.request.GET.get('order[' + str(i) + '][column]'))
            attribute = self.request.GET.get('columns[' + column + '][data]')
            direction = '-' if self.request.GET.get('order[' + str(i) + '][dir]') == 'desc' else ''
            sort.append(direction + attribute)
            i += 1

        output = self.search(limit=limit, offset=offset, sort=sort, full_text_search=full_text_search)
        if output:
            return {'draw': draw, 'recordsTotal': output.get('recordsTotal'), 'recordsFiltered': output.get('recordsFiltered'), 'data': output.get('items')}
        else:
            return {'draw': draw, 'error': self.request.localizer.translate(_('Server error'))}

    def search(self, limit=None, offset=None, search=None, sort=None, full_text_search=None):
        if not search:
            search = []
        if not sort:
            sort = []

        output = {}

        q = self.request.db_session.query(self.searched_object)
        output.update({'recordsTotal': q.count()})

        for sort_element in sort:
            if sort_element.startswith('-'):
                sort_order = 'desc'
                sort_element = sort_element.lstrip('-')
            else:
                sort_order = 'asc'

            if sort_element in self.specific_sort_methods:
                q = self.specific_sort_methods[sort_element](q, sort_order)
            elif hasattr(self.searched_object, sort_element):
                if type(getattr(self.searched_object, sort_element).type) == String:
                    q = q.order_by(getattr(func.lower(getattr(self.searched_object, sort_element)), sort_order)())
                else:
                    q = q.order_by(getattr(getattr(self.searched_object, sort_element), sort_order)())
            else:
                return

        for search_element in search:
            if hasattr(self.searched_object, search_element[0]):
                q = q.filter(getattr(self.searched_object, search_element[0]) == search_element[1])
            else:
                return

        if full_text_search:
            words = findall(r'\w+', full_text_search, UNICODE)
            for word in words:
                if self.request.db_session.bind.name == 'sqlite':
                    q = q.filter(self.full_text_search.ilike('%{}%'.format(word)))
                else:
                    q = q.filter(self.full_text_search.match(word))

        output.update({'recordsFiltered': q.count()})

        if limit:
            q = q.limit(limit)

        if offset:
            q = q.offset(offset)

        results = q.all()

        items = []
        for result in results:
            items.append(self.format_output(result))

        output.update({'items': items})
        return output

    @abstractmethod
    def format_output(self, result):
        return


class Assets(API):
    __acl__ = [
        (Allow, None, 'assets-list', 'assets-list'),
        (Allow, None, 'g:admin', 'assets-list'),
    ]

    @property
    def searched_object(self):
        return Asset

    @view_config(route_name='api-assets', request_method='GET', permission='assets-list', renderer='json')
    def list_get(self):
        return self.manage_api_queries()

    @view_config(route_name='api-datatables-assets', request_method='GET', permission='assets-list', renderer='json')
    def list_datatables_get(self):
        return self.manage_datatables_queries()

    def format_output(self, result):
        return {'id': result.id, 'asset_id': result.asset_id, 'customer': result.customer, 'site': result.site,
                'notes': result.notes, 'current_location': result.current_location,
                'status': Event.status_labels[result.history.order_by(Event.date.desc()).first().status],
                'history': [{'date': str(event.date), 'creator_id': event.creator_id, 'creator_alias': event.creator_alias, 'status': event.status} for event in result.history.order_by(Event.date).all()],
                'equipments': [{'model': equipment.family.model if equipment.family else None, 'serial_number': equipment.serial_number} for equipment in result.equipments],
                'links': [{'rel': 'self', 'href': self.request.route_path('assets-update', asset_id=result.id)}]}

    @property
    def full_text_search(self):
        return Asset.asset_id + ',' + Asset.customer + ',' + Asset.site + ',' + Asset.current_location

    @property
    def specific_sort_methods(self):
        subquery_last_status = self.request.db_session.query(Event.asset_id, Event.status, func.max(Event.date)) \
            .group_by(Event.asset_id).subquery()

        return {
            'status': lambda q, sort_order: q.outerjoin((subquery_last_status, subquery_last_status.c.asset_id == Asset.id))
                .order_by(getattr(subquery_last_status.c.status, sort_order)())
        }
    
    
def includeme(config):
    config.add_route(pattern='assets/', name='api-assets', factory=Assets)
    config.add_route(pattern='assets/datatables/', name='api-datatables-assets', factory=Assets)
