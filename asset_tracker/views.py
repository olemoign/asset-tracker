from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta
from pyramid.events import BeforeRender, subscriber
from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from pyramid.i18n import TranslationString as _
from pyramid.security import Allow
from pyramid.view import view_config

from .models import Asset, Equipment, EquipmentFamily, Event
from .utilities.authorization import rights_without_tenants


@subscriber(BeforeRender)
def add_global_variables(event):
    event['cloud_name'] = event['request'].registry.settings['asset_tracker.cloud_name']
    event['branding'] = event['request'].registry.settings.get('asset_tracker.branding', 'parsys_cloud')

    if event['request'].user:
        event['user_alias'] = event['request'].user['alias']
        event['principals'] = rights_without_tenants(event['request'].effective_principals)
        event['locale'] = event['request'].locale_name


def get_datetime(value):
    return datetime.strptime(value, '%Y-%m-%d')


class AssetsEndPoint(object):
    def __acl__(self):
        acl = [
            (Allow, None, 'assets-create', 'assets-create'),
            (Allow, None, 'assets-list', 'assets-list'),
            (Allow, None, 'g:admin', ('assets-create', 'assets-read', 'assets-update', 'assets-list')),
        ]

        if self.asset:
            acl.append((Allow, self.asset.tenant_id, 'assets-read', 'assets-read'))
            acl.append((Allow, self.asset.tenant_id, 'assets-update', 'assets-update'))

        return acl

    def __init__(self, request):
        self.request = request
        self.asset = self.get_asset()
        
    def get_asset(self):
        asset_id = self.request.matchdict.get('asset_id')
        if asset_id:
            asset = self.request.db_session.query(Asset).get(asset_id)
            if not asset:
                raise HTTPNotFound()
            else:
                return asset

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

        # noinspection PyArgumentList
        asset = Asset(asset_id=form_asset['asset_id'], tenant_id=None, customer_id=form_asset['customer_id'],
                      customer_name=form_asset['customer_name'], site=form_asset['site'],
                      current_location=form_asset['current_location'], notes=form_asset['notes'])
        self.request.db_session.add(asset)

        for form_equipment in filter(lambda item: item.get('family') or item.get('serial_number'), form_asset['equipments']):
            equipment = Equipment(family_id=form_equipment['family'], serial_number=form_equipment['serial_number'])
            asset.equipments.append(equipment)
            self.request.db_session.add(equipment)

        form_last_calibration = None
        if form_asset['last_calibration']:
            form_last_calibration = get_datetime(form_asset['last_calibration'])
            last_calibration = Event(date=form_last_calibration, creator_id=self.request.user['id'],
                                     creator_alias=self.request.user['alias'], status='calibration')
            asset.history.append(last_calibration)
            self.request.db_session.add(last_calibration)

        form_activation = None
        if form_asset['activation']:
            form_activation = get_datetime(form_asset['activation'])
            # Small trick to make sure that the activation is always stored AFTER the calibration.
            form_activation = form_activation + timedelta(hours=23, minutes=59)
            activation = Event(date=form_activation, creator_id=self.request.user['id'],
                               creator_alias=self.request.user['alias'], status='service')
            asset.history.append(activation)
            self.request.db_session.add(activation)

        form_next_calibration = None
        if form_asset['next_calibration']:
            form_next_calibration = get_datetime(form_asset['next_calibration']).date()

        if form_next_calibration:
            asset.next_calibration = form_next_calibration

        elif form_last_calibration:
            asset.next_calibration = form_last_calibration + relativedelta(years=3)

        elif form_asset['status'] == 'service':
            asset.next_calibration = datetime.utcnow().date() + relativedelta(years=3)

        elif form_activation:
            asset.next_calibration = form_activation + relativedelta(years=3)

        event = Event(date=datetime.utcnow(), creator_id=self.request.user['id'],
                      creator_alias=self.request.user['alias'], status=form_asset['status'])
        asset.history.append(event)
        self.request.db_session.add(event)

        return HTTPFound(location=self.request.route_path('assets-list'))

    @view_config(route_name='assets-update', request_method='GET', permission='assets-read',
                 renderer='assets-create_update.html')
    def update_get(self):
        last_calibration = self.asset.history.filter_by(status='calibration').order_by(Event.date.desc()).first()
        self.asset.last_calibration = last_calibration.date.date() if last_calibration else None
        activation = self.asset.history.filter_by(status='service').order_by(Event.date).first()
        self.asset.activation = activation.date.date() if activation else None

        equipments_families = self.request.db_session.query(EquipmentFamily).order_by(EquipmentFamily.model).all()
        return {'update': True, 'object': self.asset, 'equipments_families': equipments_families,
                'status': Event.status_labels}

    @view_config(route_name='assets-update', request_method='POST', permission='assets-update',
                 renderer='assets-create_update.html')
    def update_post(self):
        form_asset = self.read_form()

        if not form_asset['asset_id'] or not form_asset['tenant_id'] or not form_asset['status']:
            equipments_families = self.request.db_session.query(EquipmentFamily).order_by(EquipmentFamily.model).all()
            return {'error': _('Missing mandatory data.'), 'object': form_asset, 'status': Event.status_labels,
                    'equipments_families': equipments_families}

        self.asset.asset_id = form_asset['asset_id']
        self.asset.tenant_id = form_asset['tenant_id']
        self.asset.customer_id = form_asset['customer_id']
        self.asset.customer_name = form_asset['customer_name']
        self.asset.site = form_asset['site']
        self.asset.current_location = form_asset['current_location']
        self.asset.notes = form_asset['notes']

        if form_asset['next_calibration']:
            self.asset.next_calibration = get_datetime(form_asset['next_calibration'])

        self.asset.equipments.delete()
        for form_equipment in filter(lambda item: item.get('family') or item.get('serial_number'), form_asset['equipments']):
            equipment = Equipment(family_id=form_equipment['family'], serial_number=form_equipment['serial_number'])
            self.asset.equipments.append(equipment)
            self.request.db_session.add(equipment)

        last_status = self.asset.history.order_by(Event.date.desc()).first().status
        if form_asset['status'] != last_status:
            event = Event(date=datetime.utcnow(), creator_id=self.request.user['id'],
                          creator_alias=self.request.user['alias'], status=form_asset['status'])
            self.asset.history.append(event)
            self.request.db_session.add(event)

        if form_asset['activation']:
            form_activation = get_datetime(form_asset['activation'])
            activations = [activation.date.date() for activation in self.asset.history.filter_by(status='service').all()]

            if form_activation.date() not in activations:
                activation = Event(date=form_activation, creator_id=self.request.user['id'],
                                   creator_alias=self.request.user['alias'], status='service')
                self.asset.history.append(activation)
                self.request.db_session.add(activation)

        if form_asset['last_calibration']:
            form_last_calibration = get_datetime(form_asset['last_calibration'])
            calibrations = [calibration.date.date() for calibration in self.asset.history.filter_by(status='calibration').all()]

            if form_last_calibration.date() not in calibrations:
                calibration = Event(date=form_last_calibration, creator_id=self.request.user['id'],
                                    creator_alias=self.request.user['alias'], status='calibration')
                self.asset.history.append(calibration)
                self.request.db_session.add(calibration)

        return HTTPFound(location=self.request.route_path('assets-list'))

    @view_config(route_name='assets-list', request_method='GET', permission='assets-list', renderer='assets-list.html')
    def list_get(self):
        return {}

    def read_form(self):
        equipments_families = self.request.POST.getall('asset-equipment-family')
        equipments_serial_numbers = self.request.POST.getall('asset-equipment-serial_number')
        return {
            'asset_id': self.request.POST.get('asset-asset_id'),
            'tenant_id': self.request.POST.get('asset-tenant_id'),
            'customer_id': self.request.POST.get('asset-customer_id'),
            'customer_name': self.request.POST.get('asset-customer_name'),
            'status': self.request.POST.get('asset-status'),
            'site': self.request.POST.get('asset-site'),
            'current_location': self.request.POST.get('asset-current_location'),
            'activation': self.request.POST.get('asset-activation'),
            'last_calibration': self.request.POST.get('asset-last_calibration'),
            'next_calibration': self.request.POST.get('asset-next_calibration'),
            'equipments': [{'family': f, 'serial_number': s} for f, s in zip(equipments_families, equipments_serial_numbers)],
            'notes': self.request.POST.get('asset-notes'),
        }


def includeme(config):
    config.add_route(pattern='', name='assets-list', factory=AssetsEndPoint)
    config.add_route(pattern='create/', name='assets-create', factory=AssetsEndPoint)
    config.add_route(pattern='{asset_id}/', name='assets-update', factory=AssetsEndPoint)
