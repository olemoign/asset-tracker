"""Asset tracker datatables API."""
from parsys_utilities.api import DataTablesAPI, manage_datatables_queries
from parsys_utilities.authorization import Right
from parsys_utilities.dates import format_date
from parsys_utilities.sql import sql_search, table_from_dict
from pyramid.httpexceptions import HTTPBadRequest
from pyramid.security import Allow
from pyramid.settings import asbool
from pyramid.view import view_config
from sentry_sdk import capture_exception, capture_message

from asset_tracker import models
from asset_tracker.api.assets import Assets as AssetsAPI
from asset_tracker.constants import ADMIN_PRINCIPAL


class Assets(object):
    """List assets for dataTables."""

    __acl__ = [
        (Allow, None, 'assets-list', 'assets-list'),
        (Allow, None, ADMIN_PRINCIPAL, 'assets-list'),
    ]

    def __init__(self, request):
        self.request = request

    def tenanting(self, q):
        """Filter assets according to user's rights/tenants.
        Admins get access to all assets.

        Args:
            q (sqlalchemy.orm.query.Query): current query.

        Returns:
            sqlalchemy.orm.query.Query: filtered query.
        """
        if self.request.user.is_admin:
            return q

        else:
            authorized_tenants = {
                right.tenant
                for right in self.request.effective_principals
                if isinstance(right, Right) and right.name == 'assets-list'
            }
            return q.filter(models.Asset.tenant_id.in_(authorized_tenants))

    @view_config(route_name='api-assets', request_method='GET', permission='assets-list', renderer='json')
    def list_get(self):
        """List assets and format output according to dataTables requirements."""
        # Return if API is called by somebody other than dataTables.
        if not asbool(self.request.GET.get('datatables')):
            capture_message('Invalid API call.')
            return []

        try:
            search_parameters = manage_datatables_queries(self.request.GET)
            draw = search_parameters.pop('draw')
        except (KeyError, TypeError) as error:
            capture_exception(error)
            raise HTTPBadRequest()

        # Simulate the user's tenants as a table so that we can filter/sort on tenant_key.
        tenants = table_from_dict('tenant', self.request.user.tenants)

        full_text_search_attributes = [
            models.Asset.asset_id,
            models.Asset.current_location,
            models.Site.name,
        ]

        joined_tables = [
            (tenants, tenants.c.tenant_id == models.Asset.tenant_id),
            models.EventStatus,
            models.Site,
        ]

        specific_attributes = {
            'site': models.Site.name,
            'status': models.EventStatus.status_id,
            'tenant_key': tenants.c.parsys_key,
        }

        try:
            # noinspection PyTypeChecker
            output = sql_search(
                self.request.db_session,
                models.Asset,
                full_text_search_attributes,
                joined_tables=joined_tables,
                tenanting=self.tenanting,
                specific_attributes=specific_attributes,
                search_parameters=search_parameters,
            )

        except KeyError as error:
            capture_exception(error)
            raise HTTPBadRequest()

        tenant_keys = {tenant['id']: tenant['parsys_key'] for tenant in self.request.user.tenants}

        # Format db return for dataTables.
        assets = []
        for asset in output['items']:
            if asset.calibration_next:
                calibration_next = format_date(asset.calibration_next, self.request.locale_name)
            else:
                calibration_next = None

            status = self.request.localizer.translate(asset.status.label)
            is_active = asset.status.status_id != 'decommissioned'

            asset_output = {
                'asset_id': asset.asset_id,
                'calibration_next': calibration_next,
                'customer_name': asset.customer_name,
                'id': asset.id,
                'is_active': is_active,
                'site': asset.site.name if asset.site else None,
                'status': status,
                'tenant_key': tenant_keys[asset.tenant_id],
            }

            # Append link to output if the user is an admin or has the right to read the asset info.
            has_read_rights = Right(name='assets-read', tenant=asset.tenant_id) in self.request.effective_principals
            if self.request.user.is_admin or has_read_rights:
                link = self.request.route_path('assets-update', asset_id=asset.id)
                asset_output['links'] = [{'rel': 'self', 'href': link}]

            assets.append(asset_output)

        return {
            'data': assets,
            'draw': draw,
            'recordsFiltered': output['recordsFiltered'],
            'recordsTotal': output['recordsTotal'],
        }

    @view_config(route_name='api-assets', request_method='POST', require_csrf=False)
    def rta_link_post(self):
        """Link Station (RTA) and Asset (AssetTracker).
        Receive information from RTA about station to create/update Asset.
        """
        return AssetsAPI(self.request).rta_link_post()


class Sites(DataTablesAPI):
    """List sites for dataTables."""

    __acl__ = [
        (Allow, None, 'sites-list', 'sites-list'),
        (Allow, None, ADMIN_PRINCIPAL, 'sites-list'),
    ]

    def tenanting(self, q):
        """Filter sites according to user's rights/tenants.
        Admins get access to all sites.

        Args:
            q (sqlalchemy.orm.query.Query): current query.

        Returns:
            sqlalchemy.orm.query.Query: filtered query.
        """
        if self.request.user.is_admin:
            return q

        else:
            authorized_tenants = {
                right.tenant
                for right in self.request.effective_principals
                if isinstance(right, Right) and right.name == 'sites-list'
            }
            return q.filter(models.Site.tenant_id.in_(authorized_tenants))

    @view_config(route_name='api-sites', request_method='GET', permission='sites-list', renderer='json')
    def list_get(self):
        """List sites and format output according to dataTables requirements."""
        # Parse data from datatables.
        try:
            search_parameters = manage_datatables_queries(self.request.GET)
            draw = search_parameters.pop('draw')
        except (KeyError, TypeError) as error:
            capture_exception(error)
            raise HTTPBadRequest()

        # Simulate the user's tenants as a table so that we can filter/sort on tenant_key.
        tenants = table_from_dict('tenant', self.request.user.tenants)

        # SQL query parameters.
        full_text_search_attributes = [
            models.Site.contact,
            models.Site.email,
            models.Site.name,
            models.Site.phone,
            models.Site.site_type,
            tenants.c.parsys_key,
        ]

        joined_tables = [
            (tenants, tenants.c.tenant_id == models.Site.tenant_id),
        ]

        specific_attributes = {'tenant_key': tenants.c.parsys_key}

        try:
            # noinspection PyTypeChecker
            output = sql_search(
                db_session=self.request.db_session,
                searched_object=models.Site,
                full_text_search_attributes=full_text_search_attributes,
                joined_tables=joined_tables,
                tenanting=self.tenanting,
                specific_attributes=specific_attributes,
                search_parameters=search_parameters,
            )

        except KeyError as error:
            capture_exception(error)
            raise HTTPBadRequest()

        # dict to get tenant name from tenant id
        tenant_keys = {tenant['id']: tenant['parsys_key'] for tenant in self.request.user.tenants}

        # Format db return for dataTables.
        sites = []
        for site in output['items']:
            site_type = None
            if site.site_type:
                site_type = self.request.localizer.translate(site.site_type)

            site_output = {
                'contact': site.contact,
                'email': site.email,
                'name': site.name,
                'phone': site.phone,
                'site_type': site_type,
                'tenant_key': tenant_keys[site.tenant_id],
            }

            # Append link to output if the user is an admin or has the right to read the site info.
            has_read_rights = Right(name='sites-read', tenant=site.tenant_id) in self.request.effective_principals
            if self.request.user.is_admin or has_read_rights:
                link = self.request.route_path('sites-update', site_id=site.id)
                site_output['links'] = [{'rel': 'self', 'href': link}]

            sites.append(site_output)

        return {
            'data': sites,
            'draw': draw,
            'recordsFiltered': output['recordsFiltered'],
            'recordsTotal': output.get('recordsTotal'),
        }


def includeme(config):
    config.add_route(pattern='assets/', name='api-assets', factory=Assets)
    config.add_route(pattern='sites/', name='api-sites', factory=Sites)
