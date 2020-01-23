"""Asset tracker views: assets lists and read/update."""
from datetime import datetime
from operator import attrgetter

import json
from dateutil.relativedelta import relativedelta
from depot.manager import DepotManager
from parsys_utilities.authorization import Right
from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from pyramid.i18n import TranslationString as _
from pyramid.security import Allow
from pyramid.settings import aslist
from pyramid.view import view_config
from sentry_sdk import capture_exception
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from asset_tracker import models
from asset_tracker.constants import ADMIN_PRINCIPAL, ASSET_TYPES, CALIBRATION_FREQUENCIES_YEARS
from asset_tracker.views import FormException


class Assets(object):
    """List, read and update assets."""

    def __acl__(self):
        acl = [
            (Allow, None, 'assets-create', 'assets-create'),
            (Allow, None, 'assets-extract', 'assets-extract'),
            (Allow, None, 'assets-list', 'assets-list'),
            (Allow, None, ADMIN_PRINCIPAL, ('assets-create', 'assets-read', 'assets-update', 'assets-list')),
        ]

        if self.asset:
            acl.extend([
                (Allow, self.asset.tenant_id, 'assets-read', 'assets-read'),
                (Allow, self.asset.tenant_id, 'assets-update', 'assets-update'),
            ])

        return acl

    def __init__(self, request):
        self.request = request
        self.asset = self.get_asset()
        # Manage Marlink specifics.
        self.specific = aslist(self.request.registry.settings.get('asset_tracker.specific', []))
        self.form = None

    def get_asset(self):
        """Get in db the asset being read/updated."""
        asset_id = self.request.matchdict.get('asset_id')
        # In the list page, asset_id will be None and it's ok.
        if not asset_id:
            return

        asset = self.request.db_session.query(models.Asset).filter_by(id=asset_id) \
            .options(joinedload(models.Asset.equipments)).first()
        if not asset:
            raise HTTPNotFound()

        # By putting the translated family name at the equipment level, when can then sort equipments by translated
        # family name and serial number.
        for equipment in asset.equipments:
            if equipment.family:
                equipment.family_translated = self.request.localizer.translate(equipment.family.model)
            else:
                # Don't put None here or we won't be able to sort later.
                equipment.family_translated = ''

            if not equipment.serial_number:
                equipment.serial_number = ''

        asset.equipments.sort(key=attrgetter('family_translated', 'serial_number'))
        return asset

    def add_equipments(self):
        """Add asset's equipments."""
        groups = []
        for field in self.form:
            if field.startswith('equipment-family'):
                split_field_name = field.split('#')
                if len(split_field_name) > 1:
                    groups.append(split_field_name[1])

        for group in groups:
            family_id = self.form.get(f'equipment-family#{group}')
            if not family_id:
                continue

            family = self.request.db_session.query(models.EquipmentFamily).filter_by(family_id=family_id).first()

            equipment = models.Equipment(
                family=family,
                serial_number=self.form.get(f'equipment-serial_number#{group}'),
            )

            if family.consumable_families:
                for c_family in family.consumable_families:
                    expiration_date = self.form.get(f'equipment-expiration_date-{c_family.family_id}#{group}')

                    if expiration_date:
                        equipment.consumables.append(
                            models.Consumable(
                                family=c_family,
                                expiration_date=datetime.strptime(expiration_date, '%Y-%m-%d').date()
                            )
                        )

            self.asset.equipments.append(equipment)
            self.request.db_session.add(equipment)

    def add_event(self):
        """Add asset event."""
        if self.form.get('event_date'):
            event_date = datetime.strptime(self.form['event_date'], '%Y-%m-%d').date()
        else:
            event_date = datetime.utcnow().date()

        status = self.request.db_session.query(models.EventStatus).filter_by(status_id=self.form['event']).first()

        event = models.Event(
            date=event_date,
            creator_id=self.request.user.id,
            creator_alias=self.request.user.alias,
            status=status,
        )
        # noinspection PyProtectedMember
        self.asset._history.append(event)
        self.request.db_session.add(event)

    def add_site_change_event(self, new_site_id):
        """Add asset site change event.

        Args:
            new_site_id (int).
        """
        status = self.request.db_session.query(models.EventStatus).filter_by(status_id='site_change').first()

        event = models.Event(
            date=datetime.utcnow().date(),
            creator_id=self.request.user.id,
            creator_alias=self.request.user.alias,
            status_id=status.id,
        )

        if new_site_id:
            new_site = self.request.db_session.query(models.Site).filter_by(id=new_site_id).first()
            event.extra = json.dumps({'site_id': new_site.site_id, 'tenant_id': new_site.tenant_id})

        # noinspection PyProtectedMember
        self.asset._history.append(event)
        self.request.db_session.add(event)

    def get_base_form_data(self):
        """Get base form input data (calibration frequencies, equipments families, assets statuses, tenants)."""
        localizer = self.request.localizer
        consumables_families = {}

        equipments_families = self.request.db_session.query(models.EquipmentFamily) \
            .outerjoin(models.EquipmentFamily.consumable_families) \
            .order_by(models.EquipmentFamily.model).all()

        for equipment_family in equipments_families:
            # Translate family models so that they can be sorted translated on the page.
            equipment_family.model_translated = localizer.translate(equipment_family.model)

            if equipment_family.consumable_families:
                consumables_families[equipment_family.family_id] = {}
                for consumable_family in equipment_family.consumable_families:
                    consumables_families[equipment_family.family_id][consumable_family.family_id] = \
                        localizer.translate(consumable_family.model)

        statuses = self.request.db_session.query(models.EventStatus) \
            .filter(models.EventStatus.status_type != 'config').all()

        tenants = self.get_create_read_tenants()

        for asset_type in ASSET_TYPES:
            asset_type['label_translated'] = self.request.localizer.translate(asset_type['label'])

        return {
            'asset_types': ASSET_TYPES,
            'calibration_frequencies': CALIBRATION_FREQUENCIES_YEARS,
            'consumables_families': consumables_families,
            'equipments_families': equipments_families,
            'sites': self.get_site_data(tenants),
            'statuses': statuses,
            'tenants': tenants,
        }

    def get_expiration_dates_by_equipment_family(self):
        """Get consumables expiration dates classfied by equipment family id"""
        expiration_dates = {}

        for equipment in self.asset.equipments:
            if equipment.consumables:
                expiration_dates[equipment.id] = {}
                for consumable in equipment.consumables:
                    expiration_dates[equipment.id][consumable.family.family_id] = consumable.expiration_date

        return expiration_dates

    def get_create_read_tenants(self):
        """Get for which tenants the current user can create/read assets."""
        # Admins have access to all tenants.
        if self.request.user.is_admin:
            return self.request.user.tenants

        else:
            user_rights = self.request.effective_principals
            user_tenants = self.request.user.tenants
            return [
                tenant
                for tenant in user_tenants
                if Right(name='assets-create', tenant=tenant['id']) in user_rights
                or (self.asset and self.asset.tenant_id == tenant['id'])
            ]

    def get_latest_softwares_version(self):
        """Get last version of every softwares."""
        if not self.asset.id:
            return None

        software_updates = self.asset.history('desc') \
            .join(models.Event.status).filter(models.EventStatus.status_id == 'software_update')

        softwares = {}
        for event in software_updates:
            extra = event.extra_json
            try:
                name, version = extra['software_name'], extra['software_version']
            except KeyError as error:
                capture_exception(error)
                continue
            else:
                if name not in softwares:
                    softwares[name] = version

        return softwares

    def get_last_config(self):
        """Get last version of configuration updates."""
        last_config = self.asset.history('desc').join(models.Event.status) \
            .filter(models.EventStatus.status_id == 'config_update').first()

        if last_config is None:
            return

        return last_config.extra_json.get('config', None)

    def get_site_data(self, tenants):
        """Get all sites corresponding to current tenants. Sites will be filtered according to selected tenant in
        front/js.
        """
        tenants_ids = {tenant['id'] for tenant in tenants}

        sites = self.request.db_session.query(models.Site) \
            .filter(models.Site.tenant_id.in_(tenants_ids)) \
            .order_by(func.lower(models.Site.name))

        return {site.site_id: site for site in sites}

    def read_form(self):
        """Format form content according to our needs.
        In particular, make sure that inputs which can be list are lists in all cases, even if no data was inputed.
        """
        self.form = {
            key: value if value != '' else None
            for key, value in self.request.POST.mixed().items()
        }

        # If there is only one equipment, make sure to convert the form variables to lists so that self.add_equipments
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
        has_calibration_frequency = 'marlink' in self.specific or self.form.get('calibration_frequency')

        # We don't need asset_id or tenant_id if asset is linked.
        is_linked = self.asset and self.asset.is_linked
        needed_data = self.form.get('asset_id') and self.form.get('tenant_id')
        if (
            not is_linked and not needed_data
            or not self.form.get('asset_type')
            or not has_creation_event
            or not has_calibration_frequency
        ):
            raise FormException(_('Missing mandatory data.'), log=False)

    def remove_events(self):
        """Remove events.
        Actually, events are not removed but marked as removed in the db, so that they can be filtered later.
        """
        for event_id in self.form['event-removed']:
            event = self.request.db_session.query(models.Event).filter_by(event_id=event_id).first()
            event.removed = True
            event.removed_at = datetime.utcnow()
            event.remover_id = self.request.user.id
            event.remover_alias = self.request.user.alias

    @staticmethod
    def update_status_and_calibration_next(asset, specific):
        """Update asset status and next calibration date according to functional rules."""
        asset.status = asset.history('desc', filter_config=True).first().status

        if 'marlink' in specific:
            calibration_frequency = CALIBRATION_FREQUENCIES_YEARS['maritime']
            calibration_last = asset.calibration_last

            # If asset was calibrated (it should be, as production is considered a calibration).
            # Marlink rule: next calibration = activation date + calibration frequency.
            if calibration_last:
                activation_next = asset.history('asc').filter(models.Event.date > calibration_last) \
                    .join(models.Event.status).filter(models.EventStatus.status_id == 'service').first()
                if activation_next:
                    asset.calibration_next = activation_next.date + relativedelta(years=calibration_frequency)
                else:
                    # If asset was never activated, we consider it still should be calibrated.
                    # So calibration next = calibration last + calibration frequency.
                    asset.calibration_next = calibration_last + relativedelta(years=calibration_frequency)

            # If asset wasn't calibrated (usage problem, some assets have been put in service without having been
            # set as "produced").
            else:
                activation_first = asset.activation_first
                if activation_first:
                    asset.calibration_next = activation_first + relativedelta(years=calibration_frequency)

        else:
            # Parsys rule is straightforward: next calibration = last calibration + asset calibration frequency.
            # Calibration last is simple to get, it's just that we consider the production date as a calibration.
            calibration_last = asset.calibration_last
            if calibration_last:
                asset.calibration_next = calibration_last + relativedelta(years=asset.calibration_frequency)

    def validate_form(self):
        """Validate form data."""
        # Don't check asset_id and tenant_id if asset is linked.
        if self.asset and self.asset.is_linked:
            tenant_id = self.asset.tenant_id
        else:
            asset_id = self.form.get('asset_id')
            changed_id = not self.asset or self.asset.asset_id != asset_id
            existing_asset = self.request.db_session.query(models.Asset).filter_by(asset_id=asset_id).first()
            if changed_id and existing_asset:
                raise FormException(_('This asset id already exists.'))

            tenants_ids = [tenant['id'] for tenant in self.get_create_read_tenants()]
            tenant_id = self.form.get('tenant_id')
            if not tenant_id or tenant_id not in tenants_ids:
                raise FormException(_('Invalid tenant.'))

        calibration_frequency = self.form.get('calibration_frequency')
        if calibration_frequency and not calibration_frequency.isdigit():
            raise FormException(_('Invalid calibration frequency.'))

        site_id = self.form.get('site_id')
        model_site = self.request.db_session.query(models.Site).filter_by(id=site_id, tenant_id=tenant_id).first()
        if site_id and not model_site:
            raise FormException(_('Invalid site.'))

        if self.form.get('event'):
            status = self.request.db_session.query(models.EventStatus).filter_by(status_id=self.form['event']).first()
            if not status:
                raise FormException(_('Invalid asset status.'))

        if self.form.get('event_date'):
            try:
                datetime.strptime(self.form['event_date'], '%Y-%m-%d').date()
            except (TypeError, ValueError):
                raise FormException(_('Invalid event date.'))

        for idx, family_id in enumerate(self.form.get('equipment-family')):
            # Can contain empty strings
            if family_id:
                db_family = self.request.db_session.query(models.EquipmentFamily).filter_by(family_id=family_id).first()
                if not db_family:
                    raise FormException(_('Invalid equipment family.'))

                for c_family in db_family.consumable_families:
                    expiration_date = self.form.get(f'equipment-expiration_date-{c_family.family_id}#{idx}')
                    if expiration_date:
                        try:
                            datetime.strptime(expiration_date, '%Y-%m-%d').date()
                        except (TypeError, ValueError):
                            raise FormException(_('Invalid expiration date.'))

        for event_id in self.form['event-removed']:
            event = self.asset.history('asc', filter_config=True).filter(models.Event.event_id == event_id).first()
            if not event:
                raise FormException(_('Invalid event.'))

    @view_config(route_name='assets-create', request_method='GET', permission='assets-create',
                 renderer='pages/assets-create_update.html')
    def create_get(self):
        """Get asset create form: we only need the base form data."""
        return self.get_base_form_data()

    @view_config(route_name='assets-create', request_method='POST', permission='assets-create',
                 renderer='pages/assets-create_update.html')
    def create_post(self):
        """Post asset create form."""
        try:
            self.read_form()
            self.validate_form()
        except FormException as error:
            if error.log:
                capture_exception(error)
            return {
                'messages': [{'type': 'danger', 'text': str(error)}],
                **self.get_base_form_data(),
            }

        # Marlink has only one calibration frequency so they don't want to see the input.
        if 'marlink' in self.specific:
            calibration_frequency = CALIBRATION_FREQUENCIES_YEARS['maritime']
        else:
            calibration_frequency = int(self.form['calibration_frequency'])

        self.asset = models.Asset(
            asset_id=self.form['asset_id'],
            asset_type=self.form['asset_type'],
            calibration_frequency=calibration_frequency,
            current_location=self.form.get('current_location'),
            customer_id=self.form.get('customer_id'),
            customer_name=self.form.get('customer_name'),
            hardware_version=self.form.get('hardware_version'),
            mac_ethernet=self.form.get('mac_ethernet'),
            mac_wifi=self.form.get('mac_wifi'),
            notes=self.form.get('notes'),
            site_id=self.form.get('site_id'),
            tenant_id=self.form['tenant_id'],
        )
        self.request.db_session.add(self.asset)

        self.add_equipments()

        self.add_event()

        site_id = self.form.get('site_id')
        if site_id:
            self.add_site_change_event(site_id)

        self.update_status_and_calibration_next(self.asset, self.specific)

        return HTTPFound(location=self.request.route_path('assets-list'))

    @view_config(route_name='assets-update', request_method='GET', permission='assets-read',
                 renderer='pages/assets-create_update.html')
    def update_get(self):
        """Get asset update form: we need the base form data + the asset data."""

        return {
            'asset': self.asset,
            'asset_softwares': self.get_latest_softwares_version(),
            'expiration_dates': self.get_expiration_dates_by_equipment_family(),
            'last_config': self.get_last_config(),
            **self.get_base_form_data(),
        }

    @view_config(route_name='assets-update', request_method='POST', permission='assets-update',
                 renderer='pages/assets-create_update.html')
    def update_post(self):
        """Post asset update form."""
        try:
            self.read_form()
            self.validate_form()
        except FormException as error:
            if error.log:
                capture_exception(error)
            return {
                'asset': self.asset,
                'asset_softwares': self.get_latest_softwares_version(),
                'expiration_dates': self.get_expiration_dates_by_equipment_family(),
                'last_config': self.get_last_config(),
                'messages': [{'type': 'danger', 'text': str(error)}],
                **self.get_base_form_data(),
            }

        # Marlink has only one calibration frequency so they don't want to see the input.
        if 'marlink' in self.specific:
            self.asset.calibration_frequency = CALIBRATION_FREQUENCIES_YEARS['maritime']
        else:
            self.asset.calibration_frequency = int(self.form['calibration_frequency'])

        # No manual update if asset is linked with RTA.
        if not self.asset.is_linked:
            self.asset.asset_id = self.form['asset_id']
            self.asset.tenant_id = self.form['tenant_id']

        self.asset.asset_type = self.form['asset_type']
        self.asset.hardware_version = self.form.get('hardware_version')
        self.asset.mac_ethernet = self.form.get('mac_ethernet')
        self.asset.mac_wifi = self.form.get('mac_wifi')

        self.asset.customer_id = self.form.get('customer_id')
        self.asset.customer_name = self.form.get('customer_name')

        new_site_id = int(self.form.get('site_id')) if self.form.get('site_id') else None
        if new_site_id != self.asset.site_id:
            self.add_site_change_event(new_site_id)

        self.asset.site_id = new_site_id

        self.asset.current_location = self.form.get('current_location')

        self.asset.notes = self.form.get('notes')

        for equipment in self.asset.equipments:
            if equipment.consumables:
                for consumable in equipment.consumables:
                    self.request.db_session.delete(consumable)
            self.request.db_session.delete(equipment)
        self.add_equipments()

        if self.form.get('event'):
            self.add_event()

        # This should be done during validation but it's slightly easier here.
        # We don't rollback the transaction as we prefer to persist all other data, and just leave the events as they
        # are.
        if self.form.get('event-removed'):
            nb_removed_event = len(self.form['event-removed'])
            nb_active_event = self.asset.history('asc', filter_config=True).count()
            if nb_active_event <= nb_removed_event:
                return {
                    'asset': self.asset,
                    'asset_softwares': self.get_latest_softwares_version(),
                    'messages': [{'type': 'danger', 'text': _('Status not removed, an asset cannot have no status.')}],
                    **self.get_base_form_data(),
                }

            self.remove_events()

        self.update_status_and_calibration_next(self.asset, self.specific)

        return HTTPFound(location=self.request.route_path('assets-list'))

    @view_config(route_name='assets-list', request_method='GET', permission='assets-list',
                 renderer='pages/assets-list.html')
    def list_get(self):
        """List assets. No work done here as dataTables will call the API to get the assets list."""
        return {}

    @view_config(route_name='home', request_method='GET', permission='assets-list')
    def home_get(self):
        return HTTPFound(location=self.request.route_path('assets-list'))

    @view_config(route_name='files-asset-config', request_method='GET', permission='assets-read', renderer='json')
    def config_get(self):
        """Get configuration JSON for a given configuration update event."""
        file_id = self.request.matchdict.get('file_id')
        if not file_id:
            self.request.logger_technical.info(['missing file_id'])
            raise HTTPNotFound()

        try:
            file = DepotManager.get().get(file_id)
        except (IOError, ValueError) as error:
            capture_exception(error)
            self.request.logger_technical.info(['unknown file requested'])
            raise HTTPNotFound()

        config = file.read().decode('utf-8')
        file.close()

        return json.loads(config)


def includeme(config):
    config.add_route(pattern='assets/create/', name='assets-create', factory=Assets)
    config.add_route(pattern=r'assets/{asset_id:\d+}/', name='assets-update', factory=Assets)
    config.add_route(pattern=r'files/asset/{file_id}/', name='files-asset-config', factory=Assets)
    config.add_route(pattern='assets/', name='assets-list', factory=Assets)
    config.add_route(pattern='/', name='home', factory=Assets)
