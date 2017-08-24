from datetime import date, datetime
from operator import attrgetter

from dateutil.relativedelta import relativedelta
from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from pyramid.i18n import TranslationString as _
from pyramid.security import Allow
from pyramid.settings import aslist
from pyramid.view import view_config
from sqlalchemy.orm import joinedload

from asset_tracker.constants import CALIBRATION_FREQUENCIES_YEARS
from asset_tracker.models import Asset, Equipment, EquipmentFamily, Event, EventStatus


def get_date(value):
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        return None


class FormException(Exception):
    pass


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
        self.client_specific = aslist(self.request.registry.settings.get('asset_tracker.client_specific', []))
        self.form = None

    def get_asset(self):
        asset_id = self.request.matchdict.get('asset_id')
        if not asset_id:
            return

        asset = self.request.db_session.query(Asset).options(joinedload('equipments')).filter_by(id=asset_id).first()
        if not asset:
            raise HTTPNotFound()

        # By putting the translated family name at the equipment level, when can then sort equipments by translated
        # family name and serial number.
        for equipment in asset.equipments:
            equipment.family_translated = ''
            if equipment.family:
                equipment.family_translated = self.request.localizer.translate(equipment.family.model)

        asset.equipments.sort(key=attrgetter('family_translated', 'serial_number'))
        return asset

    def get_create_update_tenants(self):
        if self.request.user['is_admin']:
            return self.request.user['tenants']

        else:
            user_rights = self.request.effective_principals
            user_tenants = self.request.user['tenants']
            tenants_ids = {tenant['id'] for tenant in user_tenants
                           if (tenant['id'], 'assets-create') in user_rights or
                           (self.asset and self.asset.tenant_id == tenant['id'])}

            return [tenant for tenant in user_tenants if tenant['id'] in tenants_ids]

    def get_base_form_data(self):
        equipments_families = self.request.db_session.query(EquipmentFamily).order_by(EquipmentFamily.model).all()
        # Translate family models so that they can be sorted translated on the page.
        for family in equipments_families:
            family.model_translated = self.request.localizer.translate(family.model)

        statuses = self.request.db_session.query(EventStatus).all()

        tenants = self.get_create_update_tenants()

        return {'calibration_frequencies': CALIBRATION_FREQUENCIES_YEARS, 'equipments_families': equipments_families,
                'statuses': statuses, 'tenants': tenants}

    def read_form(self):
        self.form = {key: (value if value != '' else None) for key, value in self.request.POST.mixed().items()}
        # If there is only one equipment, make sure to convert the form variables to lists so that self.add_equipements
        # doesn't behave weirdly.
        equipment_families = self.form.get('equipment-family')
        if not equipment_families:
            self.form['equipment-family'] = ['']
        elif not isinstance(equipment_families, list):
            self.form['equipment-family'] = [equipment_families]

        equipment_serial_numbers = self.form.get('equipment-serial_number')
        if not equipment_serial_numbers:
            self.form['equipment-serial_number'] = ['']
        elif not isinstance(equipment_serial_numbers, list):
            self.form['equipment-serial_number'] = [self.form['equipment-serial_number']]

        if len(self.form['equipment-family']) != len(self.form['equipment-serial_number']):
            raise FormException(_('Invalid equipments.'))

        events_removed = self.form.get('event-removed')
        if not events_removed:
            self.form['event-removed'] = []
        elif not isinstance(events_removed, list):
            self.form['event-removed'] = [self.form['event-removed']]

        has_creation_event = self.asset or self.form.get('event')
        has_calibration_frequency = 'marlink' in self.client_specific or self.form.get('calibration_frequency')
        if not self.form.get('asset_id') or not self.form.get('tenant_id') or not self.form.get('asset_type') \
                or not has_creation_event or not has_calibration_frequency:
            raise FormException(_('Missing mandatory data.'))

    def validate_form(self):
        calibration_frequency = self.form.get('calibration_frequency')
        if calibration_frequency and not calibration_frequency.isdigit():
            raise FormException(_('Invalid calibration frequency.'))

        tenants_ids = [tenant['id'] for tenant in self.get_create_update_tenants()]
        if self.form['tenant_id'] not in tenants_ids:
            raise FormException(_('Invalid tenant.'))

        if self.form['event']:
            status = self.request.db_session.query(EventStatus).filter_by(status_id=self.form['event']).first()
            if not status:
                raise FormException(_('Invalid asset status.'))

        for form_family in self.form['equipment-family']:
            # form['equipment-family'] can be ['', '']
            if form_family:
                db_family = self.request.db_session.query(EquipmentFamily).filter_by(family_id=form_family).first()
                if not db_family:
                    raise FormException(_('Invalid equipment family.'))

        for event_id in self.form['event-removed']:
            event = self.request.db_session.query(Event).filter_by(event_id=event_id).first()
            if not event or event.asset_id != self.asset.id:
                raise FormException(_('Invalid event.'))

    def add_equipments(self):
        for index, family_id in enumerate(self.form['equipment-family']):
            if not family_id and not self.form['equipment-serial_number'][index]:
                continue

            if self.form['equipment-expiration_date_1'][index]:
                expiration_date_1 = get_date(self.form['equipment-expiration_date_1'][index])
            else:
                expiration_date_1 = None

            if self.form['equipment-expiration_date_2'][index]:
                expiration_date_2 = get_date(self.form['equipment-expiration_date_2'][index])
            else:
                expiration_date_2 = None

            family = self.request.db_session.query(EquipmentFamily).filter_by(family_id=family_id).first()
            equipment = Equipment(family=family,
                                  serial_number=self.form['equipment-serial_number'][index],
                                  expiration_date_1=expiration_date_1,
                                  expiration_date_2=expiration_date_2)
            self.asset.equipments.append(equipment)
            self.request.db_session.add(equipment)

    def add_event(self):
        if self.form.get('event_date'):
            event_date = get_date(self.form['event_date'])
        else:
            event_date = date.today()

        status = self.request.db_session.query(EventStatus).filter_by(status_id=self.form['event']).first()

        # noinspection PyArgumentList
        event = Event(date=event_date, creator_id=self.request.user['id'], creator_alias=self.request.user['alias'],
                      status=status)
        # noinspection PyProtectedMember
        self.asset._history.append(event)
        self.request.db_session.add(event)

    def remove_events(self):
        for event_id in self.form['event-removed']:
            event = self.request.db_session.query(Event).filter_by(event_id=event_id).first()
            event.removed = True
            event.removed_at = datetime.utcnow()
            event.remover_id = self.request.user['id']
            event.remover_alias = self.request.user['alias']

    def update_status_and_calibration_next(self):
        self.asset.status = self.asset.history('desc').first().status

        if 'marlink' in self.client_specific:
            calibration_frequency = CALIBRATION_FREQUENCIES_YEARS['maritime']
            calibration_last = self.asset.calibration_last

            # If station was calibrated (it should be, as production is considered a calibration).
            if calibration_last:
                activation_next = self.asset.history('asc').filter(Event.date > calibration_last) \
                    .join(EventStatus).filter(EventStatus.status_id == 'service').first()
                if activation_next:
                    self.asset.calibration_next = activation_next.date + relativedelta(years=calibration_frequency)
                else:
                    self.asset.calibration_next = calibration_last + relativedelta(years=calibration_frequency)

            # If station wasn't calibrated.
            else:
                activation_first = self.asset.history('asc').join(EventStatus) \
                    .filter(EventStatus.status_id == 'service').first()
                if activation_first:
                    self.asset.calibration_next = activation_first.date + relativedelta(years=calibration_frequency)

        else:
            calibration_last = self.asset.calibration_last
            if calibration_last:
                self.asset.calibration_next = calibration_last + relativedelta(years=self.asset.calibration_frequency)

    @view_config(route_name='assets-create', request_method='GET', permission='assets-create',
                 renderer='assets-create_update.html')
    def create_get(self):
        return self.get_base_form_data()

    @view_config(route_name='assets-create', request_method='POST', permission='assets-create',
                 renderer='assets-create_update.html')
    def create_post(self):
        try:
            self.read_form()
            self.validate_form()
        except FormException as error:
            return dict(error=str(error), **self.get_base_form_data())

        if 'marlink' in self.client_specific:
            calibration_frequency = CALIBRATION_FREQUENCIES_YEARS['maritime']
        else:
            calibration_frequency = int(self.form['calibration_frequency'])

        # noinspection PyArgumentList
        self.asset = Asset(asset_id=self.form['asset_id'], tenant_id=self.form['tenant_id'],
                           asset_type=self.form['asset_type'], site=self.form.get('site') or None,
                           customer_id=self.form.get('customer_id') or None,
                           customer_name=self.form.get('customer_name') or None,
                           current_location=self.form.get('current_location') or None,
                           calibration_frequency=calibration_frequency,
                           software_version=self.form.get('software_version') or None,
                           notes=self.form.get('notes') or None)
        self.request.db_session.add(self.asset)

        self.add_equipments()

        self.add_event()

        self.request.db_session.flush()

        self.update_status_and_calibration_next()

        return HTTPFound(location=self.request.route_path('assets-update', asset_id=self.asset.id))

    @view_config(route_name='assets-update', request_method='GET', permission='assets-read',
                 renderer='assets-create_update.html')
    def update_get(self):
        return dict(asset=self.asset, **self.get_base_form_data())

    @view_config(route_name='assets-update', request_method='POST', permission='assets-update',
                 renderer='assets-create_update.html')
    def update_post(self):
        try:
            self.read_form()
            self.validate_form()
        except FormException as error:
            return dict(error=str(error), asset=self.asset, **self.get_base_form_data())

        self.asset.asset_id = self.form['asset_id']
        self.asset.tenant_id = self.form['tenant_id']
        self.asset.asset_type = self.form['asset_type']
        self.asset.customer_id = self.form.get('customer_id') or None
        self.asset.customer_name = self.form.get('customer_name') or None

        self.asset.site = self.form.get('site') or None
        self.asset.current_location = self.form.get('current_location') or None
        self.asset.software_version = self.form.get('software_version') or None

        self.asset.notes = self.form.get('notes') or None

        if 'marlink' in self.client_specific:
            self.asset.calibration_frequency = CALIBRATION_FREQUENCIES_YEARS['maritime']
        else:
            self.asset.calibration_frequency = int(self.form['calibration_frequency'])

        for equipment in self.asset.equipments:
            self.request.db_session.delete(equipment)
        self.add_equipments()

        if self.form.get('event'):
            self.add_event()

        if self.form.get('event-removed'):
            self.remove_events()

        self.update_status_and_calibration_next()

        return HTTPFound(location=self.request.route_path('assets-update', asset_id=self.asset.id))

    @view_config(route_name='home', request_method='GET', permission='assets-list', renderer='assets-list.html')
    @view_config(route_name='assets-list', request_method='GET', permission='assets-list', renderer='assets-list.html')
    def list_get(self):
        return {}


def includeme(config):
    config.add_route(pattern='create/', name='assets-create', factory=AssetsEndPoint)
    config.add_route(pattern='assets/{asset_id}/', name='assets-update', factory=AssetsEndPoint)
    config.add_route(pattern='assets/', name='assets-list', factory=AssetsEndPoint)
    config.add_route(pattern='/', name='home', factory=AssetsEndPoint)
