"""Asset tracker views: assets lists and read/update."""
import json
import re
from collections import defaultdict
from datetime import datetime
from operator import attrgetter

from dateutil.relativedelta import relativedelta
from depot.manager import DepotManager
from parsys_utilities.views import AuthenticatedEndpoint
from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from pyramid.i18n import TranslationString as _
from pyramid.security import Allow
from pyramid.view import view_config
from sentry_sdk import capture_exception
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from asset_tracker import models
from asset_tracker.constants import ADMIN_PRINCIPAL, ASSET_TYPES, CALIBRATION_FREQUENCIES_YEARS
from asset_tracker.views import FormException, read_form


class Assets(metaclass=AuthenticatedEndpoint):
    """List, read and update assets."""

    __acl__ = [
        (Allow, None, 'assets-create', 'assets-create'),
        (Allow, None, 'assets-extract', 'assets-extract'),
        (Allow, None, 'assets-list', 'assets-list'),
        (Allow, None, 'assets-read', 'assets-read'),
        (Allow, None, 'assets-update', 'assets-update'),
        (Allow, None, ADMIN_PRINCIPAL, ('assets-create', 'assets-read', 'assets-update', 'assets-list')),
    ]

    def __init__(self, request):
        self.request = request
        self.asset = self.get_asset()
        # Manage Marlink specifics.
        self.config = self.request.registry.settings.get('asset_tracker.config', 'parsys')
        self.form = None

    def get_asset(self):
        """Get in db the asset being read/updated."""
        asset_id = self.request.matchdict.get('asset_id')
        # In the user/home/list pages, asset_id will be None and it's ok.
        if not asset_id:
            return

        asset = self.request.db_session.query(models.Asset).filter_by(id=asset_id) \
            .join(models.Asset.tenant) \
            .options(
                joinedload(models.Asset.equipments).joinedload(models.Equipment.family)
                    .joinedload(models.EquipmentFamily.consumable_families)  # noqa: E131
            ).first()
        if not asset:
            raise HTTPNotFound()

        # By putting the translated family name at the equipment level, when can then sort equipments by translated
        # family name and serial number.
        for equipment in asset.equipments:
            # Don't put None here or we won't be able to sort later.
            model = equipment.family.model
            equipment.family_translated = self.request.localizer.translate(model) if equipment.family else ''
            equipment.serial_number = equipment.serial_number or ''

        asset.equipments.sort(key=attrgetter('family_translated', 'serial_number'))
        return asset

    def add_equipments(self):
        """Add asset's equipments."""
        groups = []
        for field in self.form:
            match = re.match(r'(.+?)#equipment-family', field)
            if match:
                groups.append(match.group(1))

        for group in groups:
            family_id = self.form.get(f'{group}#equipment-family')
            equipment_family = self.request.db_session.query(models.EquipmentFamily).filter_by(family_id=family_id) \
                .options(joinedload(models.EquipmentFamily.consumable_families)).first()

            equipment = models.Equipment(
                family=equipment_family,
                serial_number=self.form.get(f'{group}#equipment-serial_number'),
            )

            for consumable_family in equipment_family.consumable_families:
                expiration_date = self.form.get(f'{group}#{consumable_family.family_id}-expiration_date')
                if expiration_date:
                    consumable = models.Consumable(
                        family=consumable_family,
                        expiration_date=datetime.strptime(expiration_date, '%Y-%m-%d').date(),
                    )
                    equipment.consumables.append(consumable)
                    self.request.db_session.add(consumable)

            self.asset.equipments.append(equipment)
            self.request.db_session.add(equipment)

    def add_event(self):
        """Add asset event."""
        if self.form.get('event_date'):
            event_date = datetime.strptime(self.form['event_date'], '%Y-%m-%d').date()
        else:
            event_date = datetime.utcnow().date()
        event = models.Event(
            date=event_date,
            creator_id=self.request.user.id,
            creator_alias=self.request.user.alias,
            status=self.request.db_session.query(models.EventStatus).filter_by(status_id=self.form['event']).one(),
        )
        # noinspection PyProtectedMember
        self.asset._history.append(event)
        self.request.db_session.add(event)

    def add_site_change_event(self, new_site_id):
        """Add asset site change event.

        Args:
            new_site_id (int).
        """
        event = models.Event(
            date=datetime.utcnow().date(),
            creator_id=self.request.user.id,
            creator_alias=self.request.user.alias,
            status=self.request.db_session.query(models.EventStatus).filter_by(status_id='site_change').one(),
        )

        if new_site_id:
            new_site = self.request.db_session.query(models.Site) \
                .filter_by(id=new_site_id) \
                .join(models.Site.tenant) \
                .one()
            event.extra = json.dumps({'site_id': new_site.site_id, 'tenant_id': new_site.tenant.tenant_id})

        # noinspection PyProtectedMember
        self.asset._history.append(event)
        self.request.db_session.add(event)

    def get_base_form_data(self):
        """Get base form input data (calibration frequencies, equipments families, assets statuses, tenants)."""
        localizer = self.request.localizer
        consumables_families = defaultdict(dict)

        equipments_families = self.request.db_session.query(models.EquipmentFamily) \
            .options(joinedload(models.EquipmentFamily.consumable_families)) \
            .order_by(models.EquipmentFamily.model).all()

        for equipment_family in equipments_families:
            # Translate family models so that they can be sorted translated on the page.
            equipment_family.model_translated = localizer.translate(equipment_family.model)

            for consumable_family in equipment_family.consumable_families:
                consumables_families[equipment_family.family_id][consumable_family.family_id] = \
                    localizer.translate(consumable_family.model)

        statuses = self.request.db_session.query(models.EventStatus) \
            .filter(models.EventStatus.status_type != 'config').all()

        for asset_type in ASSET_TYPES:
            asset_type['label_translated'] = self.request.localizer.translate(asset_type['label'])

        return {
            'asset_types': ASSET_TYPES,
            'calibration_frequencies': CALIBRATION_FREQUENCIES_YEARS,
            'consumables_families': consumables_families,
            'equipments_families': equipments_families,
            'sites': self.get_site_data(),
            'statuses': statuses,
            'tenants': self.request.db_session.query(models.Tenant).all(),
        }

    def get_expiration_dates_by_equipment_family(self):
        """Get consumables expiration dates classfied by equipment family id."""
        expiration_dates = defaultdict(dict)

        for equipment in self.asset.equipments:
            for consumable in equipment.consumables:
                expiration_dates[equipment.id][consumable.family.family_id] = consumable.expiration_date

        return expiration_dates

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

    def get_site_data(self):
        """Get all sites. Sites will be filtered according to selected tenant in
        front/js.
        """
        sites = self.request.db_session.query(models.Site) \
            .join(models.Site.tenant) \
            .order_by(func.lower(models.Site.name))
        return {site.site_id: site for site in sites}

    def remove_events(self):
        """Remove events.
        Actually, events are not removed but marked as removed in the db, so that they can be filtered later.
        """
        for event_id in self.form.getall('event-removed'):
            if not event_id:
                continue

            event = self.request.db_session.query(models.Event).filter_by(event_id=event_id).first()
            if not event:
                continue

            event.removed = True
            event.removed_at = datetime.utcnow()
            event.remover_id = self.request.user.id
            event.remover_alias = self.request.user.alias

    @staticmethod
    def update_status_and_calibration_next(asset):
        """Update asset status and next calibration date according to functional rules."""
        asset.status = asset.history('desc', filter_config=True).first().status

        calibration_last = asset.calibration_last
        if asset.is_decommissioned:
            asset.calibration_next = None
        elif calibration_last:
            asset.calibration_next = calibration_last + relativedelta(years=asset.calibration_frequency)

    def validate_asset(self):
        """Validate asset data."""
        has_creation_event = self.asset or self.form.get('event')
        has_calibration_frequency = self.config == 'marlink' or self.form.get('calibration_frequency')

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

        # Don't check asset_id and tenant_id if asset is linked.
        if self.asset and self.asset.is_linked:
            tenant_id = self.asset.tenant.tenant_id
        else:
            asset_id = self.form.get('asset_id')
            changed_id = not self.asset or self.asset.asset_id != asset_id
            existing_asset = self.request.db_session.query(models.Asset).filter_by(asset_id=asset_id).first()
            if changed_id and existing_asset:
                raise FormException(_('This asset id already exists.'))

            tenants_ids = self.request.db_session.query(models.Tenant.tenant_id)
            tenant_id = self.form.get('tenant_id')
            if not tenant_id or tenant_id not in [tenant_id[0] for tenant_id in tenants_ids]:
                raise FormException(_('Invalid tenant.'))

        calibration_frequency = self.form.get('calibration_frequency')
        if calibration_frequency and not calibration_frequency.isdigit():
            raise FormException(_('Invalid calibration frequency.'))

        if self.form.get('site_id'):
            model_site = self.request.db_session.query(models.Site).join(models.Site.tenant) \
                .filter(
                    models.Site.id == self.form['site_id'],
                    models.Tenant.tenant_id == tenant_id,
               ).first()
            if not model_site:
                raise FormException(_('Invalid site.'))

    def validate_equipments(self):
        """Validate equipments data."""
        equipments_families = []
        expiration_dates = []

        for field in self.form:
            match = re.match(r'(.+?)#equipment-family', field)
            if match:
                equipments_families.append(self.form[field])

            match = re.match(r'(.+?)#(.+?)-expiration_date', field)
            if match:
                expiration_dates.append(self.form[field])

        for equipments_family in equipments_families:
            db_family = self.request.db_session.query(models.EquipmentFamily) \
                .filter_by(family_id=equipments_family).first()
            if not db_family:
                raise FormException(_('Invalid equipment family.'))

        for expiration_date in expiration_dates:
            try:
                datetime.strptime(expiration_date, '%Y-%m-%d').date()
            except (TypeError, ValueError):
                raise FormException(_('Invalid expiration date.'))

    def validate_events(self):
        """Validate events data."""
        if self.form.get('event'):
            status = self.request.db_session.query(models.EventStatus).filter_by(status_id=self.form['event']).one()
            if not status:
                raise FormException(_('Invalid asset status.'))

        if self.form.get('event_date'):
            try:
                datetime.strptime(self.form['event_date'], '%Y-%m-%d').date()
            except (TypeError, ValueError):
                raise FormException(_('Invalid event date.'))

        for event_id in self.form.getall('event-removed'):
            if not event_id:
                continue

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
            self.form = read_form(self.request.POST)
            self.validate_asset()
            self.validate_equipments()
            self.validate_events()
        except FormException as error:
            if error.log:
                capture_exception(error)
            return {
                'messages': [{'type': 'danger', 'text': str(error)}],
                **self.get_base_form_data(),
            }

        # Marlink has only one calibration frequency so they don't want to see the input.
        if self.config == 'marlink':
            calibration_frequency = CALIBRATION_FREQUENCIES_YEARS['marlink']
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
            tenant=self.request.db_session.query(models.Tenant).filter_by(tenant_id=self.form['tenant_id']).one(),
        )
        self.request.db_session.add(self.asset)

        self.add_equipments()

        self.add_event()

        if self.form.get('site_id'):
            self.add_site_change_event(self.form['site_id'])

        self.update_status_and_calibration_next(self.asset)

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
            self.form = read_form(self.request.POST)
            self.validate_asset()
            self.validate_equipments()
            self.validate_events()
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
        if self.config == 'marlink':
            self.asset.calibration_frequency = CALIBRATION_FREQUENCIES_YEARS['marlink']
        else:
            self.asset.calibration_frequency = int(self.form['calibration_frequency'])

        # No manual update if asset is linked with RTA.
        if not self.asset.is_linked:
            self.asset.asset_id = self.form['asset_id']
            tenant = self.request.db_session.query(models.Tenant).filter_by(tenant_id=self.form['tenant_id']).one()
            self.asset.tenant = tenant

        self.asset.asset_type = self.form['asset_type']
        self.asset.hardware_version = self.form.get('hardware_version')
        self.asset.mac_ethernet = self.form.get('mac_ethernet')
        self.asset.mac_wifi = self.form.get('mac_wifi')

        self.asset.customer_id = self.form.get('customer_id')
        self.asset.customer_name = self.form.get('customer_name')
        self.asset.current_location = self.form.get('current_location')
        self.asset.notes = self.form.get('notes')

        event = self.form.get('event')
        if event:
            self.add_event()
        # Automatically remove site if asset is marked as being sent back to Marlink / Parsys.
        if event and event in ['transit_distributor_return', 'transit_parsys']:
            new_site_id = None
        else:
            new_site_id = int(self.form['site_id']) if self.form.get('site_id') else None
        if new_site_id != self.asset.site_id:
            self.add_site_change_event(new_site_id)
        self.asset.site_id = new_site_id

        for equipment in self.asset.equipments:
            if equipment.consumables:
                for consumable in equipment.consumables:
                    self.request.db_session.delete(consumable)
            self.request.db_session.delete(equipment)
        self.add_equipments()

        # Make sure an asset always has a status.
        if self.form.getall('event-removed'):
            nb_removed_event = len(self.form.getall('event-removed'))
            nb_active_event = self.asset.history('asc', filter_config=True).count()
            if nb_active_event > nb_removed_event:
                self.remove_events()

        self.update_status_and_calibration_next(self.asset)

        return HTTPFound(location=self.request.route_path('assets-list'))

    @view_config(route_name='assets-list', request_method='GET', permission='assets-list',
                 renderer='pages/assets-list.html')
    def list_get(self):
        """List assets. No work done here as dataTables will call the API to get the assets list."""
        return {}

    @view_config(route_name='assets-user', request_method='GET', permission='assets-read')
    def user_get(self):
        """Route used to find the asset corresponding to a given user_id, coming from RTA."""
        user_id = self.request.matchdict.get('user_id')
        asset = self.request.db_session.query(models.Asset).filter_by(user_id=user_id).first()
        if asset:
            return HTTPFound(location=self.request.route_path('assets-update', asset_id=asset.id))
        else:
            return HTTPFound(location=self.request.route_path('assets-list'))

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
        except (OSError, ValueError) as error:
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
    config.add_route(pattern=r'services/{user_id:\w{8}}/', name='assets-user', factory=Assets)
    config.add_route(pattern='/', name='home', factory=Assets)
