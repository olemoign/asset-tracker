from datetime import datetime
from traceback import format_exc

from dateutil.relativedelta import relativedelta
from parsys_utilities.authorization import rights_without_tenants
from pyramid.events import BeforeRender, subscriber
from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from pyramid.i18n import TranslationString as _
from pyramid.security import Allow
from pyramid.settings import asbool
from pyramid.view import notfound_view_config, view_config

from asset_tracker.constants import WARRANTY_DURATION_YEARS
from asset_tracker.models import Asset, Equipment, EquipmentFamily, Event, EventStatus


DEFAULT_BRANDING = 'parsys_cloud'


@subscriber(BeforeRender)
def add_global_variables(event):
    event['cloud_name'] = event['request'].registry.settings['asset_tracker.cloud_name']
    event['branding'] = event['request'].registry.settings.get('asset_tracker.branding', DEFAULT_BRANDING)
    event['csrf_token'] = event['request'].session.get_csrf_token()

    if event['request'].user:
        event['user_alias'] = event['request'].user['alias']
        event['principals'] = event['request'].effective_principals
        event['principals_without_tenants'] = rights_without_tenants(event['request'].effective_principals)
        event['locale'] = event['request'].locale_name


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

    def get_asset(self):
        asset_id = self.request.matchdict.get('asset_id')
        if asset_id:
            asset = self.request.db_session.query(Asset).get(asset_id)
            if not asset:
                raise HTTPNotFound()
            else:
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
        form = {key: (value if value != '' else None) for key, value in self.request.POST.mixed().items()}
        # If there is only one equipment, make sure to convert the form variables to lists so that self.add_equipements
        # doesn't behave weirdly.
        if not isinstance(form['equipment-family'], list):
            form['equipment-family'] = [form['equipment-family']]
        if not isinstance(form['equipment-serial_number'], list):
            form['equipment-serial_number'] = [form['equipment-serial_number']]

        if not form['asset_id'] or not form['tenant_id'] or (not self.asset and not form['event']):
            raise FormException(_('Missing mandatory data.'))

        return form

    def validate_form(self, form):
        tenants_ids = [tenant['id'] for tenant in self.get_create_update_tenants()]
        if form['tenant_id'] not in tenants_ids:
            raise FormException(_('Invalid tenant.'))

        if form['event']:
            status = self.request.db_session.query(EventStatus).filter_by(status_id=form['event']).first()
            if not status:
                raise FormException(_('Invalid asset status.'))

        for form_family in form['equipment-family']:
            # form['equipment-family'] can be ['', '']
            if form_family:
                db_family = self.request.db_session.query(EquipmentFamily).filter_by(family_id=form_family).first()
                if not db_family:
                    raise FormException(_('Invalid equipment family.'))

    def add_equipments(self, form, asset):
        for index, value in enumerate(form['equipment-family']):
            family = self.request.db_session.query(EquipmentFamily).filter_by(family_id=value).first()
            # In the case where we have multiple equipments, we can get '' as serial number, I prefer to persist None.
            if form['equipment-serial_number'][index] == '':
                form['equipment-serial_number'][index] = None
            equipment = Equipment(family=family, serial_number=form['equipment-serial_number'][index])
            asset.equipments.append(equipment)
            self.request.db_session.add(equipment)

    def add_event(self, form, asset):
        if form['event_date']:
            event_date = get_date(form['event_date'])
        else:
            event_date = datetime.utcnow().replace(microsecond=0)

        status = self.request.db_session.query(EventStatus).filter_by(status_id=form['event']).first()

        # noinspection PyArgumentList
        event = Event(date=event_date, creator_id=self.request.user['id'], creator_alias=self.request.user['alias'],
                      status=status)
        asset.history.append(event)
        self.request.db_session.add(event)

    @view_config(route_name='assets-create', request_method='GET', permission='assets-create',
                 renderer='assets-create_update.html')
    def create_get(self):
        return self.get_base_form_data()

    @view_config(route_name='assets-create', request_method='POST', permission='assets-create',
                 renderer='assets-create_update.html')
    def create_post(self):
        try:
            form = self.read_form()
            self.validate_form(form)
        except FormException as error:
            return dict(error=str(error), **self.get_base_form_data())

        # noinspection PyArgumentList
        asset = Asset(asset_id=form['asset_id'], tenant_id=form['tenant_id'], site=form['site'],
                      customer_id=form['customer_id'], customer_name=form['customer_name'],
                      current_location=form['current_location'], software_version=form['software_version'],
                      notes=form['notes'])
        self.request.db_session.add(asset)

        self.add_equipments(form, asset)

        self.add_event(form, asset)

        self.request.db_session.flush()

        return HTTPFound(location=self.request.route_path('assets-update', asset_id=asset.id))

    @view_config(route_name='assets-update', request_method='GET', permission='assets-read',
                 renderer='assets-create_update.html')
    def update_get(self):
        production = self.asset.history.join(EventStatus).filter(EventStatus.status_id == 'manufactured') \
            .order_by(Event.date).first()
        self.asset.production = production.date.date() if production else None

        activation = self.asset.history.join(EventStatus).filter(EventStatus.status_id == 'service') \
            .order_by(Event.date).first()
        self.asset.activation = activation.date.date() if activation else None

        calibration_last = self.asset.history.join(EventStatus).filter(EventStatus.status_id == 'calibration') \
            .order_by(Event.date.desc()).first()
        self.asset.calibration_last = calibration_last.date.date() if calibration_last else None

        if self.asset.activation:
            self.asset.warranty_end = self.asset.activation + relativedelta(years=WARRANTY_DURATION_YEARS)

        return dict(update=True, asset=self.asset, **self.get_base_form_data())

    @view_config(route_name='assets-update', request_method='POST', permission='assets-update',
                 renderer='assets-create_update.html')
    def update_post(self):
        try:
            form = self.read_form()
            self.validate_form(form)
        except FormException as error:
            return dict(update=True, error=str(error), asset=self.asset, **self.get_base_form_data())

        self.asset.asset_id = form['asset_id']
        self.asset.tenant_id = form['tenant_id']
        self.asset.customer_id = form['customer_id']
        self.asset.customer_name = form['customer_name']
        self.asset.site = form['site']
        self.asset.current_location = form['current_location']
        self.asset.software_version = form['software_version']
        self.asset.notes = form['notes']

        self.asset.equipments.delete()
        self.add_equipments(form, self.asset)

        if form['event']:
            self.add_event(form, self.asset)

        return HTTPFound(location=self.request.route_path('assets-update', asset_id=self.asset.id))

    @view_config(route_name='home', request_method='GET', permission='assets-list', renderer='assets-list.html')
    @view_config(route_name='assets-list', request_method='GET', permission='assets-list', renderer='assets-list.html')
    def list_get(self):
        return {}


@notfound_view_config(append_slash=True, renderer='errors/404.html')
def not_found_get(request):
    request.response.status_int = 404
    return {}


@view_config(context=Exception, renderer='errors/500.html')
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
