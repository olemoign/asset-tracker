from datetime import datetime
from operator import attrgetter
from traceback import format_exc

from dateutil.relativedelta import relativedelta
from parsys_utilities.authorization import rights_without_tenants
from parsys_utilities.model import joinedload
from pyramid.events import BeforeRender, subscriber
from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from pyramid.i18n import TranslationString as _
from pyramid.security import Allow
from pyramid.settings import asbool
from pyramid.view import exception_view_config, notfound_view_config, view_config

from asset_tracker.constants import WARRANTY_DURATION_YEARS
from asset_tracker.models import Asset, Equipment, EquipmentFamily, Event, EventStatus


DEFAULT_BRANDING = 'parsys_cloud'


@subscriber(BeforeRender)
def add_global_variables(event):
    event['cloud_name'] = event['request'].registry.settings['asset_tracker.cloud_name']
    event['branding'] = event['request'].registry.settings.get('asset_tracker.branding', DEFAULT_BRANDING)
    event['csrf_token'] = event['request'].session.get_csrf_token()

    event['principals'] = event['request'].effective_principals
    event['principals_without_tenants'] = rights_without_tenants(event['request'].effective_principals)
    event['locale'] = event['request'].locale_name

    if event['request'].user:
        event['user_alias'] = event['request'].user['alias']


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
        self.form = None

    def get_asset(self):
        asset_id = self.request.matchdict.get('asset_id')
        if not asset_id:
            return

        asset = self.request.db_session.query(Asset).options(joinedload('equipments')).get(asset_id)
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

        return {'equipments_families': equipments_families, 'statuses': statuses, 'tenants': tenants}

    def read_form(self):
        self.form = {key: (value if value != '' else None) for key, value in self.request.POST.mixed().items()}
        # If there is only one equipment, make sure to convert the form variables to lists so that self.add_equipements
        # doesn't behave weirdly.
        if not isinstance(self.form['equipment-family'], list):
            self.form['equipment-family'] = [self.form['equipment-family']]
        if not isinstance(self.form['equipment-serial_number'], list):
            self.form['equipment-serial_number'] = [self.form['equipment-serial_number']]

        if self.form.get('event-removed') and not isinstance(self.form['event-removed'], list):
            self.form['event-removed'] = [self.form['event-removed']]

        if not self.form['asset_id'] or not self.form['tenant_id'] or (not self.asset and not self.form['event']):
            raise FormException(_('Missing mandatory data.'))

    def validate_form(self):
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

        for event_id in self.form.get('event-removed', []):
            event = self.request.db_session.query(Event).filter_by(event_id=event_id).first()
            if not event or event.asset_id != self.asset.id:
                raise FormException(_('Invalid event.'))

    def add_equipments(self):
        for index, family_id in enumerate(self.form['equipment-family']):
            if not family_id and not self.form['equipment-serial_number'][index]:
                continue

            family = self.request.db_session.query(EquipmentFamily).filter_by(family_id=family_id).first()
            equipment = Equipment(family=family, serial_number=self.form['equipment-serial_number'][index])
            self.asset.equipments.append(equipment)
            self.request.db_session.add(equipment)

    def add_event(self):
        if self.form['event_date']:
            event_date = get_date(self.form['event_date'])
        else:
            event_date = datetime.utcnow().replace(microsecond=0)

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
            event.removed_date = datetime.utcnow()
            event.remover_id = self.request.user['id']
            event.remover_alias = self.request.user['alias']

    def update_status_and_calibration_next(self):
        pass

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

        # noinspection PyArgumentList
        self.asset = Asset(asset_id=self.form['asset_id'], tenant_id=self.form['tenant_id'], type=self.form['type'],
                           site=self.form['site'], customer_id=self.form['customer_id'],
                           customer_name=self.form['customer_name'], current_location=self.form['current_location'],
                           software_version=self.form['software_version'], notes=self.form['notes'])
        self.request.db_session.add(self.asset)

        self.add_equipments()

        self.add_event()

        self.request.db_session.flush()

        return HTTPFound(location=self.request.route_path('assets-update', asset_id=self.asset.id))

    @view_config(route_name='assets-update', request_method='GET', permission='assets-read',
                 renderer='assets-create_update.html')
    def update_get(self):
        production_first = self.asset.history('asc').join(EventStatus) \
            .filter(EventStatus.status_id == 'manufactured').first()
        self.asset.production = production_first.date.date() if production_first else None

        if self.asset.activation_first:
            self.asset.warranty_end = self.asset.activation_first + relativedelta(years=WARRANTY_DURATION_YEARS)

        return dict(update=True, asset=self.asset, **self.get_base_form_data())

    @view_config(route_name='assets-update', request_method='POST', permission='assets-update',
                 renderer='assets-create_update.html')
    def update_post(self):
        try:
            self.read_form()
            self.validate_form()
        except FormException as error:
            return dict(update=True, error=str(error), asset=self.asset, **self.get_base_form_data())

        self.asset.asset_id = self.form['asset_id']
        self.asset.tenant_id = self.form['tenant_id']
        self.asset.type = self.form['type']
        self.asset.customer_id = self.form['customer_id']
        self.asset.customer_name = self.form['customer_name']
        self.asset.site = self.form['site']
        self.asset.current_location = self.form['current_location']
        self.asset.software_version = self.form['software_version']
        self.asset.notes = self.form['notes']

        for equipment in self.asset.equipments:
            self.request.db_session.delete(equipment)
        self.add_equipments()

        if self.form['event']:
            self.add_event()

        if self.form.get('event-removed'):
            self.remove_events()

        return HTTPFound(location=self.request.route_path('assets-update', asset_id=self.asset.id))

    @view_config(route_name='home', request_method='GET', permission='assets-list', renderer='assets-list.html')
    @view_config(route_name='assets-list', request_method='GET', permission='assets-list', renderer='assets-list.html')
    def list_get(self):
        return {}


@notfound_view_config(append_slash=True, renderer='errors/404.html')
def not_found_get(request):
    request.response.status_int = 404
    return {}


@exception_view_config(Exception, renderer='errors/500.html')
def exception_view(request):
    debug_exceptions = asbool(request.registry.settings.get('asset_tracker.dev.debug_exceptions', False))
    if debug_exceptions:
        raise request.exception

    else:
        error_header = 'Time: {}\nUrl: {}\nMethod: {}\n'.format(datetime.utcnow(), request.url, request.method)
        error_text = error_header + format_exc()

        subject = 'Exception on {}'.format(request.host_url)
        message = {'email': {'subject': subject, 'text': error_text}}
        request.notifier.notify(message, level='exception')

        request.logger_actions.error(error_text)

        request.response.status_int = 500
        return {}


def includeme(config):
    config.add_route(pattern='create/', name='assets-create', factory=AssetsEndPoint)
    config.add_route(pattern='assets/{asset_id}/', name='assets-update', factory=AssetsEndPoint)
    config.add_route(pattern='assets/', name='assets-list', factory=AssetsEndPoint)
    config.add_route(pattern='/', name='home', factory=AssetsEndPoint)
