"""Asset tracker datatables API."""
from parsys_utilities.api import DataTablesAPI, manage_datatables_queries
from parsys_utilities.authorization import authenticate_rta, get_tenantless_principals
from parsys_utilities.dates import format_date
from parsys_utilities.sql import sql_search, table_from_dict
from pyramid.httpexceptions import HTTPBadRequest
from pyramid.security import Allow, Everyone
from pyramid.settings import asbool
from pyramid.view import view_config
from sentry_sdk import capture_exception, capture_message
from sqlalchemy import cast, Unicode as String

from asset_tracker import models
from asset_tracker.api.assets import Assets as AssetsAPI
from asset_tracker.constants import ADMIN_PRINCIPAL


class Assets:
    """List assets for dataTables."""

    def __acl__(self):
        acl = [
            (Allow, None, 'assets-list', 'assets-list'),
            (Allow, None, ADMIN_PRINCIPAL, 'assets-list'),
        ]

        if authenticate_rta(self.request):
            acl.extend([
                (Allow, None, Everyone, 'api-assets-create'),
            ])

        return acl

    def __init__(self, request):
        self.request = request

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

        config = self.request.registry.settings.get('asset_tracker.config', 'parsys')
        statuses_dict = [
            {'id': status.id, 'label': self.request.localizer.translate(status.label(config))}
            for status in self.request.db_session.query(models.EventStatus)
        ]
        # Simulate the assets statuses as a table with translated labels so that we can filter/sort on status.
        statuses = table_from_dict('status', statuses_dict)

        full_text_search_attributes = [
            models.Asset.asset_id,
            models.Asset.current_location,
            models.Site.name,
            models.TenantInfo.name,
        ]

        # tables_from_dict makes all columns as strings.
        joined_tables = [
            (statuses, statuses.c.id == cast(models.Asset.status_id, String)),
            models.Asset.site,
            models.Asset.tenant_info,
        ]

        specific_attributes = {
            'site': models.Site.name,
            'status': statuses.c.label,
            'tenant_name': models.TenantInfo.name,
        }

        try:
            # noinspection PyTypeChecker
            output = sql_search(
                self.request.db_session,
                models.Asset,
                full_text_search_attributes,
                joined_tables=joined_tables,
                specific_attributes=specific_attributes,
                search_parameters=search_parameters,
            )

        except KeyError as error:
            capture_exception(error)
            raise HTTPBadRequest()

        # Format db return for dataTables.
        assets = []
        for asset in output['items']:
            c_next = asset.calibration_next
            asset_output = {
                'asset_id': asset.asset_id,
                'calibration_next': format_date(c_next, self.request.locale_name) if c_next else None,
                'customer_name': asset.customer_name,
                'id': asset.id,
                'is_active': asset.status.status_id != 'decommissioned',
                'site': asset.site.name if asset.site else None,
                'status': self.request.localizer.translate(asset.status.label(config)),
                'tenant_name': asset.tenant_info.name,
            }

            # Append link to output if the user is an admin or has the right to read the asset info.
            has_read_rights = 'assets-read' in get_tenantless_principals(self.request.effective_principals)
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

    @view_config(route_name='api-assets', request_method='POST', permission='api-assets-create', require_csrf=False,
                 renderer='json')
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

        # SQL query parameters.
        full_text_search_attributes = [
            models.Site.contact,
            models.Site.email,
            models.Site.name,
            models.Site.phone,
            models.Site.site_type,
            models.TenantInfo.name,
        ]

        # tables_from_dict makes all columns as strings.
        joined_tables = [
            models.Site.tenant_info,
        ]

        specific_attributes = {
            'tenant_name': models.TenantInfo.name,
        }

        try:
            # noinspection PyTypeChecker
            output = sql_search(
                self.request.db_session,
                models.Site,
                full_text_search_attributes,
                joined_tables=joined_tables,
                specific_attributes=specific_attributes,
                search_parameters=search_parameters,
            )

        except KeyError as error:
            capture_exception(error)
            raise HTTPBadRequest()

        # Format db return for dataTables.
        sites = []
        for site in output['items']:
            site_output = {
                'contact': site.contact,
                'email': site.email,
                'name': site.name,
                'phone': site.phone,
                'site_type': self.request.localizer.translate(site.site_type) if site.site_type else None,
                'tenant_name': site.tenant_info.name,
            }

            # Append link to output if the user is an admin or has the right to read the site info.
            has_read_rights = 'sites-read' in get_tenantless_principals(self.request.effective_principals)
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
