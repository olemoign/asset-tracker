"""Asset tracker views: assets lists and read/update."""

from datetime import datetime
from operator import attrgetter

from dateutil.relativedelta import relativedelta
from parsys_utilities.sentry import sentry_capture_exception
from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from pyramid.i18n import TranslationString as _
from pyramid.security import Allow
from pyramid.settings import aslist
from pyramid.view import view_config
from sqlalchemy.orm import joinedload

from asset_tracker.constants import CALIBRATION_FREQUENCIES_YEARS
from asset_tracker.models import Asset, Equipment, EquipmentFamily, Event, EventStatus


class FormException(Exception):
    pass


class AssetsEndPoint(object):
    """List, read and update assets."""

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
        # Manage Marlink specifics.
        self.client_specific = aslist(self.request.registry.settings.get('asset_tracker.client_specific', []))
        self.form = None

    def get_asset(self):
        """Get in db the asset being read/updated."""
        asset_id = self.request.matchdict.get('asset_id')
        # In the list page, asset_id will be None and it's ok.
        if not asset_id:
            return

        asset = self.request.db_session.query(Asset).options(joinedload('equipments')).filter_by(id=asset_id).first()
        if not asset:
            raise HTTPNotFound()

        # By putting the translated family name at the equipment level, when can then sort equipments by translated
        # family name and serial number.
        for equipment in asset.equipments:
            # Don't put None here or we won't be able to sort later.
            equipment.family_translated = ''
            if equipment.family:
                equipment.family_translated = self.request.localizer.translate(equipment.family.model)

        asset.equipments.sort(key=attrgetter('family_translated', 'serial_number'))
        return asset

    def get_latest_softwares_version(self):
        """Get last version of every softwares."""
        if not self.asset.id:
            return None  # no available software for new Asset

        software_updates = self.asset.history('desc') \
            .join(EventStatus).filter(EventStatus.status_id == 'software_update')

        softwares = {}
        for event in software_updates:
            extra = event.extra_json
            try:
                name, version = extra['software_name'], extra['software_version']
            except KeyError:
                sentry_capture_exception(self.request, level='info')
                continue
            else:
                if name not in softwares:
                    softwares[name] = version

        return softwares

    def get_create_read_tenants(self):
        """Get for which tenants the current user can create/read assets."""
        # Admins have access to all tenants.
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
        """Get base form input data (calibration frequencies, equipments families, assets statuses, tenants)."""
        equipments_families = self.request.db_session.query(EquipmentFamily).order_by(EquipmentFamily.model).all()
        # Translate family models so that they can be sorted translated on the page.
        for family in equipments_families:
            family.model_translated = self.request.localizer.translate(family.model)

        statuses = self.request.db_session.query(EventStatus).all()

        tenants = self.get_create_read_tenants()

        return {'calibration_frequencies': CALIBRATION_FREQUENCIES_YEARS, 'equipments_families': equipments_families,
                'statuses': statuses, 'tenants': tenants}

    def read_form(self):
        """Format form content according to our needs.
        In particular, make sure that inputs which can be list are lists in all cases, even if no data was inputed.

        """
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

        expiration_dates_1 = self.form.get('equipment-expiration_date_1')
        if not expiration_dates_1:
            self.form['equipment-expiration_date_1'] = ['']
        elif not isinstance(expiration_dates_1, list):
            self.form['equipment-expiration_date_1'] = [expiration_dates_1]

        expiration_dates_2 = self.form.get('equipment-expiration_date_2')
        if not expiration_dates_2:
            self.form['equipment-expiration_date_2'] = ['']
        elif not isinstance(expiration_dates_2, list):
            self.form['equipment-expiration_date_2'] = [expiration_dates_2]

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
        """Validate form data."""
        calibration_frequency = self.form.get('calibration_frequency')
        if calibration_frequency and not calibration_frequency.isdigit():
            raise FormException(_('Invalid calibration frequency.'))

        tenants_ids = [tenant['id'] for tenant in self.get_create_read_tenants()]
        tenant_id = self.form.get('tenant_id')
        if not tenant_id or tenant_id not in tenants_ids:
            raise FormException(_('Invalid tenant.'))

        if self.form.get('event'):
            status = self.request.db_session.query(EventStatus).filter_by(status_id=self.form['event']).first()
            if not status:
                raise FormException(_('Invalid asset status.'))

        if self.form.get('event_date'):
            try:
                datetime.strptime(self.form['event_date'], '%Y-%m-%d').date()
            except (TypeError, ValueError):
                raise FormException(_('Invalid event date.'))

        for family_id, expiration_date_1, expiration_date_2 in zip(self.form['equipment-family'],
                                                                   self.form['equipment-expiration_date_1'],
                                                                   self.form['equipment-expiration_date_2']):
            # form['equipment-family'] can be ['', '']
            if family_id:
                db_family = self.request.db_session.query(EquipmentFamily).filter_by(family_id=family_id).first()
                if not db_family:
                    raise FormException(_('Invalid equipment family.'))
                if expiration_date_1:
                    try:
                        datetime.strptime(expiration_date_1, '%Y-%m-%d').date()
                    except (TypeError, ValueError):
                        raise FormException(_('Invalid expiration date.'))
                if expiration_date_2:
                    try:
                        datetime.strptime(expiration_date_2, '%Y-%m-%d').date()
                    except (TypeError, ValueError):
                        raise FormException(_('Invalid expiration date.'))

        for event_id in self.form['event-removed']:
            event = self.asset.history('asc', filter_software=True).filter(Event.event_id == event_id).first()
            if not event:
                raise FormException(_('Invalid event.'))

    def add_equipments(self):
        """Add asset's equipments."""
        # Equipment box can be completely empty.
        zip_equipment = zip(self.form['equipment-family'],
                            self.form['equipment-serial_number'],
                            self.form['equipment-expiration_date_1'],
                            self.form['equipment-expiration_date_2'])
        for family_id, serial_number, expiration_date_1, expiration_date_2 in zip_equipment:
            if not family_id and not serial_number:
                continue

            if expiration_date_1:
                expiration_date_1 = datetime.strptime(expiration_date_1, '%Y-%m-%d').date()
            else:
                expiration_date_1 = None

            if expiration_date_2:
                expiration_date_2 = datetime.strptime(expiration_date_2, '%Y-%m-%d').date()
            else:
                expiration_date_2 = None

            family = self.request.db_session.query(EquipmentFamily).filter_by(family_id=family_id).first()
            equipment = Equipment(family=family,
                                  serial_number=serial_number,
                                  expiration_date_1=expiration_date_1,
                                  expiration_date_2=expiration_date_2)
            self.asset.equipments.append(equipment)
            self.request.db_session.add(equipment)

    def add_event(self):
        """Add asset event."""
        if self.form.get('event_date'):
            event_date = datetime.strptime(self.form['event_date'], '%Y-%m-%d').date()
        else:
            event_date = datetime.utcnow().date()

        status = self.request.db_session.query(EventStatus).filter_by(status_id=self.form['event']).first()

        # noinspection PyArgumentList
        event = Event(date=event_date, creator_id=self.request.user['id'], creator_alias=self.request.user['alias'],
                      status=status)
        # noinspection PyProtectedMember
        self.asset._history.append(event)
        self.request.db_session.add(event)

    def remove_events(self):
        """Remove events.
        Actually, events are not removed but marked as removed in the db, so that they can be filtered later.

        """
        for event_id in self.form['event-removed']:
            event = self.request.db_session.query(Event).filter_by(event_id=event_id).first()
            event.removed = True
            event.removed_at = datetime.utcnow()
            event.remover_id = self.request.user['id']
            event.remover_alias = self.request.user['alias']

    @staticmethod
    def update_status_and_calibration_next(asset, client_specific):
        """Update asset status and next calibration date according to functional rules."""
        asset.status = asset.history('desc', filter_software=True).first().status

        if 'marlink' in client_specific:
            calibration_frequency = CALIBRATION_FREQUENCIES_YEARS['maritime']
            calibration_last = asset.calibration_last

            # If asset was calibrated (it should be, as production is considered a calibration).
            # Marlink rule: next calibration = activation date + calibration frequency.
            if calibration_last:
                activation_next = asset.history('asc').filter(Event.date > calibration_last) \
                    .join(EventStatus).filter(EventStatus.status_id == 'service').first()
                if activation_next:
                    asset.calibration_next = activation_next.date + relativedelta(years=calibration_frequency)
                else:
                    # If asset was never activated, we consider it still should be calibrated.
                    # So calibration next = calibration last + calibration frequency.
                    asset.calibration_next = calibration_last + relativedelta(years=calibration_frequency)

            # If asset wasn't calibrated (usage problem, some assets have been put in service without having been
            # set as "produced").
            else:
                activation_first = asset.history('asc').join(EventStatus) \
                    .filter(EventStatus.status_id == 'service').first()
                if activation_first:
                    asset.calibration_next = activation_first.date + relativedelta(years=calibration_frequency)

        else:
            # Parsys rule is straightforward: next calibration = last calibration + asset calibration frequency.
            # Calibration last is simple to get, it's just that we consider the production date as a calibration.
            calibration_last = asset.calibration_last
            if calibration_last:
                asset.calibration_next = calibration_last + relativedelta(years=asset.calibration_frequency)

    @view_config(route_name='assets-create', request_method='GET', permission='assets-create',
                 renderer='assets-create_update.html')
    def create_get(self):
        """Get asset create form: we only need the base form data."""
        return self.get_base_form_data()

    @view_config(route_name='assets-create', request_method='POST', permission='assets-create',
                 renderer='assets-create_update.html')
    def create_post(self):
        """Post asset create form."""
        try:
            self.read_form()
            self.validate_form()
        except FormException as error:
            sentry_capture_exception(self.request, level='info')
            return dict(error=str(error), **self.get_base_form_data())

        # Marlink has only one calibration frequency so they don't want to see the input.
        if 'marlink' in self.client_specific:
            calibration_frequency = CALIBRATION_FREQUENCIES_YEARS['maritime']
        else:
            calibration_frequency = int(self.form['calibration_frequency'])

        # noinspection PyArgumentList
        self.asset = Asset(asset_id=self.form['asset_id'], tenant_id=self.form['tenant_id'],
                           asset_type=self.form['asset_type'], site=self.form.get('site'),
                           customer_id=self.form.get('customer_id'), customer_name=self.form.get('customer_name'),
                           current_location=self.form.get('current_location'),
                           calibration_frequency=calibration_frequency,
                           notes=self.form.get('notes'))
        self.request.db_session.add(self.asset)

        self.add_equipments()

        self.add_event()

        self.update_status_and_calibration_next(self.asset, self.client_specific)

        return HTTPFound(location=self.request.route_path('assets-update', asset_id=self.asset.id))

    @view_config(route_name='assets-update', request_method='GET', permission='assets-read',
                 renderer='assets-create_update.html')
    def update_get(self):
        """Get asset update form: we need the base form data + the asset data."""
        return dict(asset=self.asset, asset_softwares=self.get_latest_softwares_version(), **self.get_base_form_data())

    @view_config(route_name='assets-update', request_method='POST', permission='assets-update',
                 renderer='assets-create_update.html')
    def update_post(self):
        """Post asset update form."""
        try:
            self.read_form()
            self.validate_form()
        except FormException as error:
            sentry_capture_exception(self.request, level='info')
            return dict(error=str(error), asset=self.asset,
                        asset_softwares=self.get_latest_softwares_version(), **self.get_base_form_data())

        # no manual update if asset is linked with RTA
        if not self.asset.is_linked:
            self.asset.asset_id = self.form['asset_id']
            self.asset.tenant_id = self.form['tenant_id']

        self.asset.asset_type = self.form['asset_type']

        self.asset.customer_id = self.form.get('customer_id')
        self.asset.customer_name = self.form.get('customer_name')

        self.asset.site = self.form.get('site')
        self.asset.current_location = self.form.get('current_location')

        self.asset.notes = self.form.get('notes')

        # Marlink has only one calibration frequency so they don't want to see the input.
        if 'marlink' in self.client_specific:
            self.asset.calibration_frequency = CALIBRATION_FREQUENCIES_YEARS['maritime']
        else:
            self.asset.calibration_frequency = int(self.form['calibration_frequency'])

        for equipment in self.asset.equipments:
            self.request.db_session.delete(equipment)
        self.add_equipments()

        if self.form.get('event'):
            self.add_event()

        # This should be done during validation but it's slightly easier here.
        # We don't rollback the transaction as we prefer to persist all other data, and just leave the events as they
        # are.
        if self.form.get('event-removed'):
            nb_removed_event = len(self.form['event-removed'])
            nb_active_event = self.asset.history('asc', filter_software=True).count()
            if nb_active_event <= nb_removed_event:
                error = _('Status not removed, an asset cannot have no status.')
                return dict(error=error, asset=self.asset,
                            asset_softwares=self.get_latest_softwares_version(), **self.get_base_form_data())

            self.remove_events()

        self.update_status_and_calibration_next(self.asset, self.client_specific)

        return HTTPFound(location=self.request.route_path('assets-update', asset_id=self.asset.id))

    @view_config(route_name='home', request_method='GET', permission='assets-list', renderer='assets-list.html')
    @view_config(route_name='assets-list', request_method='GET', permission='assets-list', renderer='assets-list.html')
    def list_get(self):
        """List assets. No work done here as dataTables will call the API to get the assets list."""
        return {}


def includeme(config):
    config.add_route(pattern='create/', name='assets-create', factory=AssetsEndPoint)
    config.add_route(pattern='assets/{asset_id:\d+}/', name='assets-update', factory=AssetsEndPoint)
    config.add_route(pattern='assets/', name='assets-list', factory=AssetsEndPoint)
    config.add_route(pattern='/', name='home', factory=AssetsEndPoint)
