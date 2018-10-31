"""Site tracker views: sites lists and read/update."""
from parsys_utilities.sentry import sentry_exception
from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from pyramid.i18n import TranslationString as _
from pyramid.security import Allow
from pyramid.view import view_config

from asset_tracker import models
from asset_tracker.constants import FormException

SITE_TYPES = [_('Company'), _('Hospital'), _('Nursing home'), _('Ship')]


class Sites(object):
    """List, read and update sites."""

    def __acl__(self):
        acl = [
            (Allow, None, 'sites-create', 'sites-create'),
            (Allow, None, 'sites-list', 'sites-list'),
            (Allow, None, 'g:admin', ('sites-create', 'sites-read', 'sites-update', 'sites-list')),
        ]

        if self.site:
            acl.append((Allow, self.site.tenant_id, 'sites-read', 'sites-read'))
            acl.append((Allow, self.site.tenant_id, 'sites-update', 'sites-update'))

        return acl

    def __init__(self, request):
        self.request = request
        self.site = self.get_site()
        self.form = None

    def get_site(self):
        """Get in db the site being read/updated."""
        site_id = self.request.matchdict.get('site_id')
        if not site_id:
            return None  # In the list page, site_id will be None and it's ok.

        site = self.request.db_session.query(models.Site).filter_by(id=site_id).first()
        if not site:
            raise HTTPNotFound()

        return site

    def get_base_form_data(self):
        """Get base form input data: site types, ordered by translated label, and tenants."""
        return {
            'site_types': sorted(SITE_TYPES, key=self.request.localizer.translate),
            'tenants': self.get_create_read_tenants(),
        }

    def get_create_read_tenants(self):
        """Get for which tenants the current user can create/read sites."""
        # Admins have access to all tenants.
        if self.request.user.is_admin:
            return self.request.user.tenants

        else:
            user_rights = self.request.effective_principals
            user_tenants = self.request.user.tenants
            tenants_ids = {tenant['id'] for tenant in user_tenants
                           if (tenant['id'], 'sites-create') in user_rights or
                           (self.site and self.site.tenant_id == tenant['id'])}

            return [tenant for tenant in user_tenants if tenant['id'] in tenants_ids]

    def read_form(self):
        """Format form content."""
        self.form = {key: (value.strip() if value.strip() != '' else None)
                     for key, value in self.request.POST.mixed().items()}

    def validate_form(self):
        """Validate form data."""
        tenants_ids = [tenant['id'] for tenant in self.get_create_read_tenants()]
        tenant_id = self.form.get('tenant_id')
        if not tenant_id or tenant_id not in tenants_ids:
            raise FormException(_('Invalid tenant.'), log=True)

        site_name = self.form.get('name')
        if not site_name:
            raise FormException(_('Name is required.'))

        if not self.site or self.site.name != site_name:
            existing_site = self.request.db_session.query(models.Site).filter_by(name=site_name).first()
            if existing_site:
                raise FormException(_('Name already exists.'))

        site_type = self.form.get('site_type')
        if not site_type:
            raise FormException(_('Site type is required.'))

    @view_config(route_name='sites-create', request_method='GET', permission='sites-create',
                 renderer='sites-create_update.html')
    def create_get(self):
        """Get site create form."""
        return self.get_base_form_data()

    @view_config(route_name='sites-create', request_method='POST', permission='sites-create',
                 renderer='sites-create_update.html')
    def create_post(self):
        """Post site create form."""
        try:
            self.read_form()
            self.validate_form()

        except FormException as error:
            if error.log:
                sentry_exception(self.request, level='info')
            return {'error': str(error), **self.get_base_form_data()}

        # noinspection PyArgumentList
        self.site = models.Site(
            # required
            tenant_id=self.form['tenant_id'],
            name=self.form['name'],
            site_type=self.form['site_type'],

            # optional
            contact=self.form.get('contact'),
            phone=self.form.get('phone'),
            email=self.form.get('email'),
        )

        self.request.db_session.add(self.site)
        self.request.db_session.flush()

        return HTTPFound(location=self.request.route_path('sites-list'))

    @view_config(route_name='sites-update', request_method='GET', permission='sites-read',
                 renderer='sites-create_update.html')
    def update_get(self):
        """Get site update form: we need the site data."""
        return {'site': self.site, **self.get_base_form_data()}

    @view_config(route_name='sites-update', request_method='POST', permission='sites-update',
                 renderer='sites-create_update.html')
    def update_post(self):
        """Post site update form."""
        try:
            self.read_form()
            self.validate_form()

        except FormException as error:
            if error.log:
                sentry_exception(self.request, level='info')
            return {'error': str(error), 'site': self.site, **self.get_base_form_data()}

        # required
        self.site.tenant_id = self.form['tenant_id']
        self.site.name = self.form['name']
        self.site.site_type = self.form['site_type']

        # optional
        self.site.contact = self.form.get('contact')
        self.site.phone = self.form.get('phone')
        self.site.email = self.form.get('email')

        return HTTPFound(location=self.request.route_path('sites-list'))

    @view_config(route_name='sites-list', request_method='GET', permission='sites-list',
                 renderer='sites-list.html')
    def list_get(self):
        """List sites. No work done here as dataTables will call the API to get the sites list."""
        return {}


def includeme(config):
    config.add_route(pattern='sites/create/', name='sites-create', factory=Sites)
    config.add_route(pattern=r'sites/{site_id:\d+}/', name='sites-update', factory=Sites)
    config.add_route(pattern='sites/', name='sites-list', factory=Sites)
