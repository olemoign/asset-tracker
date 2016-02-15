from datetime import date, datetime
from logging import getLogger

from pyramid.events import BeforeRender, subscriber
from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from pyramid.i18n import TranslationString as _
from pyramid.security import Allow
from pyramid.view import view_config

from .models import Asset, Equipment, EquipmentFamily, Event
from .utilities.authorization import rights_without_tenants

logger = getLogger('asset_tracker')


@subscriber(BeforeRender)
def add_global_variables(event):
    if event['request'].user:
        event['user_alias'] = event['request'].user['alias']
        event['principals'] = rights_without_tenants(event['request'].effective_principals)
        event['locale'] = event['request'].locale_name


class AssetsEndPoint(object):
    __acl__ = [
        (Allow, None, 'assets-create', 'assets-create'),
        (Allow, None, 'assets-update', 'assets-update'),
        (Allow, None, 'assets-list', 'assets-list'),
        (Allow, None, 'g:admin', ('assets-create', 'assets-update', 'assets-list')),
    ]

    def __init__(self, request):
        self.request = request

    @view_config(route_name='assets-create', request_method='GET', permission='assets-create',
                 renderer='assets-create_update.html')
    def create_get(self):
        equipments_families = self.request.db_session.query(EquipmentFamily).order_by(EquipmentFamily.model).all()
        return {'equipments_families': equipments_families, 'status': Event.status_labels}

    @view_config(route_name='assets-create', request_method='POST', permission='assets-create',
                 renderer='assets-create_update.html')
    def create_post(self):
        form_asset = self.read_form()

        if not form_asset['status'] or not form_asset['asset_id']:
            equipments_families = self.request.db_session.query(EquipmentFamily).order_by(EquipmentFamily.model).all()
            return {'error': _('Missing mandatory data.'), 'object': form_asset,
                    'equipments_families': equipments_families, 'status': Event.status_labels}

        # TODO-OLM: tenanting
        asset = Asset(tenant_id=None, asset_id=form_asset['asset_id'],
                      customer=form_asset['customer'], site=form_asset['site'],
                      current_location=form_asset['current_location'], notes=form_asset['notes'])
        self.request.db_session.add(asset)

        for form_equipment in filter(lambda item: item.get('family') or item.get('serial_number'), form_asset['equipments']):
            equipment = Equipment(family_id=form_equipment['family'], serial_number=form_equipment['serial_number'])
            asset.equipments.append(equipment)
            self.request.db_session.add(equipment)

        today = date.today()
        activation_date = None
        if form_asset['activation_date']:
            activation_date = datetime.strptime(form_asset['activation_date'], '%Y-%m-%d').date()
        if activation_date and activation_date < today:
            activation = Event(date=activation_date, creator_id=self.request.user['id'],
                               creator_alias=self.request.user['alias'], status='service')
            asset.history.append(activation)
            self.request.db_session.add(activation)

        calibration_date = None
        if form_asset['last_calibration_date']:
            calibration_date = datetime.strptime(form_asset['last_calibration_date'], '%Y-%m-%d').date()
        if calibration_date and calibration_date != today:
            calibration = Event(date=calibration_date, creator_id=self.request.user['id'],
                                creator_alias=self.request.user['alias'], status='calibration')
            asset.history.append(calibration)
            self.request.db_session.add(calibration)

        if form_asset['status'] == 'service' and not calibration_date:
            calibration = Event(date=datetime.utcnow(), creator_id=self.request.user['id'],
                                creator_alias=self.request.user['alias'], status='calibration')
            asset.history.append(calibration)
            self.request.db_session.add(calibration)

        event = Event(date=datetime.utcnow(), creator_id=self.request.user['id'],
                      creator_alias=self.request.user['alias'], status=form_asset['status'])
        asset.history.append(event)
        self.request.db_session.add(event)

        return HTTPFound(location=self.request.route_path('assets-list'))

    @view_config(route_name='assets-update', request_method='GET', permission='assets-update',
                 renderer='assets-create_update.html')
    def update_get(self):
        asset_id = self.request.matchdict['asset_id']
        asset = self.request.db_session.query(Asset).get(asset_id)

        if asset:
            last_calibration_date = asset.history.filter_by(status='calibration').order_by(Event.date.desc()).first()
            asset.last_calibration_date = last_calibration_date.date.date() if last_calibration_date else None
            activation_date = asset.history.filter_by(status='service').order_by(Event.date).first()
            asset.activation_date = activation_date.date.date() if activation_date else None

            equipments_families = self.request.db_session.query(EquipmentFamily).order_by(EquipmentFamily.model).all()
            return {'update': True, 'object': asset, 'equipments_families': equipments_families,
                    'status': Event.status_labels}
        else:
            return HTTPNotFound()

    @view_config(route_name='assets-update', request_method='POST', permission='assets-update',
                 renderer='assets-create_update.html')
    def update_post(self):
        asset_id = self.request.matchdict['asset_id']
        asset = self.request.db_session.query(Asset).get(asset_id)

        if asset:
            form_asset = self.read_form()

            if not form_asset['status'] or not form_asset['asset_id']:
                equipments_families = self.request.db_session.query(EquipmentFamily).order_by(EquipmentFamily.model).all()
                return {'error': _('Missing mandatory data.'), 'object': form_asset,
                        'equipments_families': equipments_families, 'status': Event.status_labels}

            asset.asset_id = form_asset['asset_id']
            asset.customer = form_asset['customer']
            asset.site = form_asset['site']
            asset.current_location = form_asset['current_location']
            asset.notes = form_asset['notes']

            asset.equipments.delete()
            for form_equipment in filter(lambda item: item.get('family') or item.get('serial_number'), form_asset['equipments']):
                equipment = Equipment(family_id=form_equipment['family'], serial_number=form_equipment['serial_number'])
                asset.equipments.append(equipment)
                self.request.db_session.add(equipment)

            if form_asset['status'] != asset.history.order_by(Event.date.desc()).first().status:
                event = Event(date=datetime.utcnow(), creator_id=self.request.user['id'],
                              creator_alias=self.request.user['alias'], status=form_asset['status'])
                asset.history.append(event)
                self.request.db_session.add(event)

            activation = asset.history.filter_by(status='service').order_by(Event.date).first()
            activation_date = activation.date.date() if activation else None
            form_activation_date = None
            if form_asset['activation_date']:
                form_activation_date = datetime.strptime(form_asset['activation_date'], '%Y-%m-%d').date()
            if form_activation_date and form_activation_date < activation_date:
                activation = Event(date=form_activation_date, creator_id=self.request.user['id'],
                                   creator_alias=self.request.user['alias'], status='service')
                asset.history.append(activation)
                self.request.db_session.add(activation)

            today = date.today()
            calibrations = asset.history.filter_by(status='service').order_by(Event.date).all()
            calibrations_date = [x.date.date() for x in calibrations]
            form_calibration_date = None
            if form_asset['last_calibration_date']:
                form_calibration_date = datetime.strptime(form_asset['last_calibration_date'], '%Y-%m-%d').date()
            if form_calibration_date and form_calibration_date < today and form_calibration_date not in calibrations_date:
                calibration = Event(date=form_calibration_date, creator_id=self.request.user['id'],
                                    creator_alias=self.request.user['alias'], status='calibration')
                asset.history.append(calibration)
                self.request.db_session.add(calibration)

            return HTTPFound(location=self.request.route_path('assets-list'))
        else:
            return HTTPNotFound()

    @view_config(route_name='assets-list', request_method='GET', permission='assets-list', renderer='assets-list.html')
    def list_get(self):
        return {}

    def read_form(self):
        equipments_families = self.request.POST.getall('asset-equipment-family')
        equipments_serial_numbers = self.request.POST.getall('asset-equipment-serial_number')
        return {
            'status': self.request.POST.get('asset-status'),
            'asset_id': self.request.POST.get('asset-asset_id'),
            'customer': self.request.POST.get('asset-customer'),
            'site': self.request.POST.get('asset-site'),
            'last_calibration_date': self.request.POST.get('asset-last_calibration_date'),
            'activation_date': self.request.POST.get('asset-activation_date'),
            'current_location': self.request.POST.get('asset-current_location'),
            'equipments': [{'family': f, 'serial_number': s} for f, s in zip(equipments_families, equipments_serial_numbers)],
            'notes': self.request.POST.get('asset-notes'),
        }


def includeme(config):
    config.add_route(pattern='', name='assets-list', factory=AssetsEndPoint)
    config.add_route(pattern='create/', name='assets-create', factory=AssetsEndPoint)
    config.add_route(pattern='{asset_id}/', name='assets-update', factory=AssetsEndPoint)
