"""Site tracker views: sites lists and read/update."""
from pyramid.security import Allow
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from pyramid.i18n import TranslationString as _

from parsys_utilities.sentry import sentry_capture_exception

from asset_tracker import models


class FormException(Exception):
    pass


class SitesEndPoint(object):
    """List, read and update sites."""

    def __acl__(self):  # TODO update asset
        acl = [
            (Allow, None, 'assets-create', 'assets-create'),
            (Allow, None, 'assets-list', 'assets-list'),
            (Allow, None, 'g:admin', ('sites-create', 'sites-read', 'sites-update', 'sites-list')),
        ]

        if self.site:
            acl.append((Allow, self.site.tenant_id, 'assets-read', 'assets-read'))
            acl.append((Allow, self.site.tenant_id, 'assets-update', 'assets-update'))

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
            return HTTPNotFound()

        return site

    def get_create_read_tenants(self):
        """Get for which tenants the current user can create/read sites."""

        # Admins have access to all tenants.
        if self.request.user['is_admin']:
            return self.request.user['tenants']

        else:
            user_rights = self.request.effective_principals
            user_tenants = self.request.user['tenants']
            tenants_ids = {tenant['id'] for tenant in user_tenants
                           if (tenant['id'], 'sites-create') in user_rights or
                           (self.site and self.site.tenant_id == tenant['id'])}

            return [tenant for tenant in user_tenants if tenant['id'] in tenants_ids]

    def read_form(self):
        """Format form content."""
        self.form = {key: (value if value != '' else None) for key, value in self.request.POST.mixed().items()}

    def validate_form(self):
        """Validate form data."""

        tenants_ids = [tenant['id'] for tenant in self.get_create_read_tenants()]
        tenant_id = self.form.get('tenant_id')
        if not tenant_id or tenant_id not in tenants_ids:
            raise FormException(_('Invalid tenant.'))

        site_type = self.form.get('type')
        if not site_type:
            raise FormException(_('Type is required.'))
        elif not self.site and self.request.db_session.query(models.Site).filter_by(type=site_type).first():
            raise FormException(_('Type already exist.'))

        # TODO validate contact / phone / email ?

    def get_base_form_data(self):
        """Get base form input data (tenants)."""

        return {
            'tenants': self.get_create_read_tenants(),
        }

    @view_config(route_name='sites-create', request_method='GET', permission='sites-create',
                 renderer='sites-create_update.html')
    def create_get(self):
        """Get site create form."""

        return dict(**self.get_base_form_data())

    @view_config(route_name='sites-create', request_method='POST', permission='sites-create',
                 renderer='sites-create_update.html')
    def create_post(self):
        """Post site create form."""

        try:
            self.read_form()
            self.validate_form()

        except FormException as error:
            sentry_capture_exception(self.request, level='info')
            return dict(error=str(error), **self.get_base_form_data())

        # noinspection PyArgumentList
        self.site = models.Site(
            # required
            tenant_id=self.form['tenant_id'],
            type=self.form['type'],

            # optional
            contact=self.form.get('contact'),
            phone=self.form.get('phone'),
            email=self.form.get('email'),
        )

        self.request.db_session.add(self.site)
        self.request.db_session.flush()

        return HTTPFound(location=self.request.route_path('sites-update', site_id=self.site.id))

    @view_config(route_name='sites-update', request_method='GET', permission='sites-read',
                 renderer='sites-create_update.html')
    def update_get(self):
        """Get site update form: we need the site data."""

        return dict(site=self.site, **self.get_base_form_data())

    @view_config(route_name='sites-update', request_method='POST', permission='sites-update',
                 renderer='sites-create_update.html')
    def update_post(self):
        """Post site update form."""

        try:
            self.read_form()
            self.validate_form()

        except FormException as error:
            sentry_capture_exception(self.request, level='info')
            return dict(error=str(error), site=self.site, **self.get_base_form_data())

        # required
        self.site.tenant_id = self.form['tenant_id']
        self.site.type = self.form['type']

        # optional
        self.site.contact = self.form.get('contact')
        self.site.phone = self.form.get('phone')
        self.site.email = self.form.get('email')

        return HTTPFound(location=self.request.route_path('sites-update', site_id=self.site.id))

    @view_config(route_name='sites-list', request_method='GET', permission='sites-list',
                 renderer='sites-list.html')
    def list_get(self):
        """List sites. No work done here as dataTables will call the API to get the sites list."""

        return dict()


def includeme(config):
    config.add_route(pattern='sites/create/', name='sites-create', factory=SitesEndPoint)
    config.add_route(pattern='sites/{site_id:\d+}/', name='sites-update', factory=SitesEndPoint)
    config.add_route(pattern='sites/', name='sites-list', factory=SitesEndPoint)
