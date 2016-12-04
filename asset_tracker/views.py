from datetime import datetime
from traceback import format_exc

from parsys_utilities.authorization import rights_without_tenants
from pyramid.events import BeforeRender, subscriber
from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from pyramid.i18n import TranslationString as _
from pyramid.security import Allow
from pyramid.settings import asbool
from pyramid.view import notfound_view_config, view_config

from asset_tracker.models import Asset, Equipment, EquipmentFamily, Event


@subscriber(BeforeRender)
def add_global_variables(event):
    event['cloud_name'] = event['request'].registry.settings['asset_tracker.cloud_name']
    event['branding'] = event['request'].registry.settings.get('asset_tracker.branding', 'parsys_cloud')
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
    def __init__(self, msg, form):
        self.msg = msg
        self.form = form
        super().__init__()


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

    def get_base_form_data(self):
        if self.request.user['is_admin'] or not self.asset:
            tenants = self.request.user['tenants']
        else:
            tenants = [tenant for tenant in self.request.user['tenants']
                       if (tenant['id'], 'assets-create') in self.request.effective_principals or
                       tenant['id'] == self.asset.tenant_id]
        equipments_families = self.request.db_session.query(EquipmentFamily).order_by(EquipmentFamily.model).all()
        return {'equipments_families': equipments_families, 'status': Event.status_labels, 'tenants': tenants}

    def read_form(self, update):
        form = {key: (value if value != '' else None) for key, value in self.request.POST.mixed().items()}
        form['equipment-family'] = form['equipment-family'] or []
        form['equipment-serial_number'] = form['equipment-serial_number'] or []

        if not form['asset_id'] or not form['tenant_id'] or (not update and not form['event']):
            raise FormException(_('Missing mandatory data.'), form)

        return form

    @view_config(route_name='assets-create', request_method='GET', permission='assets-create',
                 renderer='assets-create_update.html')
    def create_get(self):
        return self.get_base_form_data()

    @view_config(route_name='assets-create', request_method='POST', permission='assets-create',
                 renderer='assets-create_update.html')
    def create_post(self):
        try:
            form_asset = self.read_form(update=False)
        except FormException as error:
            return dict(error=error.msg, asset=error.form, **self.get_base_form_data())

        if not self.request.user['is_admin'] and \
                (form_asset['tenant_id'], 'assets-create') not in self.request.effective_principals:
            return dict(error=_('Invalid tenant.'), asset=form_asset, **self.get_base_form_data())

        # noinspection PyArgumentList
        asset = Asset(asset_id=form_asset['asset_id'], tenant_id=form_asset['tenant_id'], site=form_asset['site'],
                      customer_id=form_asset['customer_id'], customer_name=form_asset['customer_name'],
                      current_location=form_asset['current_location'], software_version=form_asset['software_version'],
                      notes=form_asset['notes'])
        self.request.db_session.add(asset)

        for index, value in enumerate(form_asset['equipment-family']):
            equipment = Equipment(family_id=value, serial_number=form_asset['equipment-serial_number'][index])
            asset.equipments.append(equipment)
            self.request.db_session.add(equipment)

        event = Event(date=datetime.utcnow(), creator_id=self.request.user['id'],
                      creator_alias=self.request.user['alias'], status=form_asset['event'])
        asset.history.append(event)
        self.request.db_session.add(event)

        self.request.db_session.flush()

        return HTTPFound(location=self.request.route_path('assets-update', asset_id=asset.id))

    @view_config(route_name='assets-update', request_method='GET', permission='assets-read',
                 renderer='assets-create_update.html')
    def update_get(self):
        production = self.asset.history.filter_by(status='produced').order_by(Event.date).first()
        self.asset.production = production.date.date() if production else None

        activation = self.asset.history.filter_by(status='service').order_by(Event.date).first()
        self.asset.activation = activation.date.date() if activation else None

        last_calibration = self.asset.history.filter_by(status='calibration').order_by(Event.date.desc()).first()
        self.asset.calibration_last = last_calibration.date.date() if last_calibration else None

        # TODO
        self.asset.calibration_next = None
        self.asset.calibration_end = None
        self.asset.warranty_end = None

        return dict(update=True, asset=self.asset, **self.get_base_form_data())

    @view_config(route_name='assets-update', request_method='POST', permission='assets-update',
                 renderer='assets-create_update.html')
    def update_post(self):
        try:
            form_asset = self.read_form(update=True)
        except FormException as error:
            error.form.update({'id': self.asset.id, 'history': self.asset.history})
            return dict(error=error.msg, update=True, asset=error.form, **self.get_base_form_data())

        manager_has_right = form_asset['tenant_id'] == self.asset.tenant_id or \
            (form_asset['tenant_id'], 'assets-create') in self.request.effective_principals
        if not self.request.user['is_admin'] and not manager_has_right:
            form_asset.update({'id': self.asset.id, 'history': self.asset.history})
            return dict(error=_('Invalid tenant.'), update=True, asset=form_asset, **self.get_base_form_data())

        self.asset.asset_id = form_asset['asset_id']
        self.asset.tenant_id = form_asset['tenant_id']
        self.asset.customer_id = form_asset['customer_id']
        self.asset.customer_name = form_asset['customer_name']
        self.asset.site = form_asset['site']
        self.asset.current_location = form_asset['current_location']
        self.asset.software_version = form_asset['software_version']
        self.asset.notes = form_asset['notes']

        self.asset.equipments.delete()
        for index, value in enumerate(form_asset['equipment-family']):
            equipment = Equipment(family_id=value, serial_number=form_asset['equipment-serial_number'][index])
            self.asset.equipments.append(equipment)
            self.request.db_session.add(equipment)

        if form_asset['event']:
            event_date = get_date(form_asset['event_date']) if form_asset['event_date'] else datetime.utcnow()
            event = Event(date=event_date, creator_id=self.request.user['id'], creator_alias=self.request.user['alias'],
                          status=form_asset['event'])
            self.asset.history.append(event)

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
        error_text = 'Method: {}\n\nUrl: {}\n\n'.format(request.method, request.url) + format_exc()
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
