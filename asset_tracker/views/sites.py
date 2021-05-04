"""Site tracker views: sites lists and read/update."""
from operator import itemgetter

from parsys_utilities.views import AuthenticatedEndpoint
from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from pyramid.i18n import TranslationString as _
from pyramid.security import Allow
from pyramid.view import view_config
from sentry_sdk import capture_exception
from sqlalchemy.orm import joinedload

from asset_tracker import models
from asset_tracker.constants import ADMIN_PRINCIPAL, SITE_TYPES
from asset_tracker.views import FormException, read_form


class Sites(metaclass=AuthenticatedEndpoint):
    """List, read and update sites."""

    __acl__ = [
        (Allow, None, 'sites-create', 'sites-create'),
        (Allow, None, 'sites-list', 'sites-list'),
        (Allow, None, 'sites-read', 'sites-read'),
        (Allow, None, 'sites-update', 'sites-update'),
        (Allow, None, ADMIN_PRINCIPAL, ('sites-create', 'sites-read', 'sites-update', 'sites-list')),
    ]

    def __init__(self, request):
        self.request = request
        self.site = self.get_site()
        self.form = None

    def get_site(self):
        """Get in db the site being read/updated."""
        site_id = self.request.matchdict.get('site_id')
        if not site_id:
            return None  # In the list page, site_id will be None and it's ok.

        site = self.request.db_session.query(models.Site).filter_by(id=site_id) \
            .join(models.Asset.tenant) \
            .options(joinedload(models.Site.assets).joinedload(models.Asset.status)) \
            .first()
        if not site:
            raise HTTPNotFound()

        return site

    def get_past_assets(self):
        """Retrieve which assets were ever present on the site."""
        past_assets = []

        # Get all assets who have ever been on a site (this includes current assets).
        # site_id is stored in models.Event.extra in JSON. Filtering gets complicated.
        # noinspection PyProtectedMember
        assets_ever_on_site = self.request.db_session.query(models.Asset) \
            .join(models.Asset._history).filter(models.Event.extra.ilike(f'%"site_id": "{self.site.site_id}"%')) \
            .join(models.Event.status).filter(models.EventStatus.status_id == 'site_change')

        # For each asset, check if there is a site change AFTER arrival on the site. This could happen multiple times.
        for asset in assets_ever_on_site:
            # noinspection PyProtectedMember
            site_changes = self.request.db_session.query(models.Event) \
                .filter(models.Event.asset == asset) \
                .join(models.Event.status).filter(models.EventStatus.status_id == 'site_change').all()

            for index, site_change in enumerate(site_changes):
                if index == 0:
                    continue

                if site_changes[index - 1].extra_json.get('site_id') == self.site.site_id:
                    past_assets.append({
                        'asset_id': asset.asset_id,
                        'asset_type': asset.asset_type,
                        'id': asset.id,
                        'start': site_changes[index - 1].created_at,
                        'end': site_change.created_at,
                    })

        return sorted(past_assets, key=itemgetter('start'))

    def validate_site(self):
        """Validate form data."""
        tenants_ids = self.request.db_session.query(models.Tenant.tenant_id)
        tenant_id = self.form.get('tenant_id')
        if not tenant_id or tenant_id not in [tenant_id[0] for tenant_id in tenants_ids]:
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
                 renderer='pages/sites-create_update.html')
    def create_get(self):
        """Get site create form."""
        return {
            'site_types': sorted(SITE_TYPES, key=self.request.localizer.translate),
            'tenants': self.request.db_session.query(models.Tenant).all(),
        }

    @view_config(route_name='sites-create', request_method='POST', permission='sites-create',
                 renderer='pages/sites-create_update.html')
    def create_post(self):
        """Post site create form."""
        try:
            self.form = read_form(self.request.POST)
            self.validate_site()
        except FormException as error:
            if error.log:
                capture_exception(error)
            return {
                'messages': [{'type': 'danger', 'text': str(error)}],
                'site_types': sorted(SITE_TYPES, key=self.request.localizer.translate),
                'tenants': self.request.db_session.query(models.Tenant).all(),
            }

        self.site = models.Site(
            contact=self.form.get('contact'),
            email=self.form.get('email'),
            name=self.form['name'],
            phone=self.form.get('phone'),
            site_type=self.form['site_type'],
            tenant=self.request.db_session.query(models.Tenant).filter_by(tenant_id=self.form['tenant_id']).one(),
        )

        self.request.db_session.add(self.site)
        self.request.db_session.flush()

        return HTTPFound(location=self.request.route_path('sites-list'))

    @view_config(route_name='sites-update', request_method='GET', permission='sites-read',
                 renderer='pages/sites-create_update.html')
    def update_get(self):
        """Get site update form: we need the site data."""
        return {
            'past_assets': self.get_past_assets(),
            'site': self.site,
            'site_types': sorted(SITE_TYPES, key=self.request.localizer.translate),
            'tenants': self.request.db_session.query(models.Tenant).all(),
        }

    @view_config(route_name='sites-update', request_method='POST', permission='sites-update',
                 renderer='pages/sites-create_update.html')
    def update_post(self):
        """Post site update form."""
        try:
            self.form = read_form(self.request.POST)
            self.validate_site()
        except FormException as error:
            if error.log:
                capture_exception(error)
            return {
                'messages': [{'type': 'danger', 'text': str(error)}],
                'site': self.site,
                'site_types': sorted(SITE_TYPES, key=self.request.localizer.translate),
                'tenants': self.request.db_session.query(models.Tenant).all(),
            }

        # If the site changed tenant, remove it from assets with the old tenant.
        if self.site.tenant.tenant_id != self.form['tenant_id']:
            self.site.assets = []

        # Required.
        tenant = self.request.db_session.query(models.Tenant).filter_by(tenant_id=self.form['tenant_id']).one()
        self.site.tenant = tenant
        self.site.name = self.form['name']
        self.site.site_type = self.form['site_type']

        # Optional.
        self.site.contact = self.form.get('contact')
        self.site.phone = self.form.get('phone')
        self.site.email = self.form.get('email')

        return HTTPFound(location=self.request.route_path('sites-list'))

    @view_config(route_name='sites-list', request_method='GET', permission='sites-list',
                 renderer='pages/sites-list.html')
    def list_get(self):
        """List sites. No work done here as dataTables will call the API to get the sites list."""
        return {}


def includeme(config):
    config.add_route(pattern='sites/create/', name='sites-create', factory=Sites)
    config.add_route(pattern=r'sites/{site_id:\d+}/', name='sites-update', factory=Sites)
    config.add_route(pattern='sites/', name='sites-list', factory=Sites)
