from parsys_utilities.authorization import Right
from pyramid.httpexceptions import HTTPForbidden
from pyramid.security import Allow
from pyramid.view import view_config
from sentry_sdk import capture_message

from asset_tracker import models
from asset_tracker.constants import ADMIN_PRINCIPAL


class Sites(object):
    """(Cloud) get site info in consultation."""
    __acl__ = [
        (Allow, None, 'sites-list', 'sites-list'),
        (Allow, None, ADMIN_PRINCIPAL, 'sites-list'),
    ]

    def __init__(self, request):
        self.request = request

    @view_config(route_name='api-sites-read', request_method='GET', renderer='sites-information.html')
    def read_get(self):
        """Get site information for consultation, HTML response to insert directly into the consultation.

        Always returns a 200, even if the site doesn't exist or the user hasn't got the rights. This way the user
        doesn't get an error message, just an empty iframe.

        """
        site_id = self.request.matchdict.get('site_id')

        site = self.request.db_session.query(models.Site).filter_by(site_id=site_id).first()
        if not site:
            capture_message('Missing site.')
            return {}

        # If the user isn't authenticated yet, make sure he does the roundtrip with RTA.
        if not self.request.user:
            raise HTTPForbidden()

        if Right(name='api-sites-read', tenant=site.tenant_id) not in self.request.effective_principals:
            capture_message('Forbidden site request.')
            return {}

        return {
            'contact': site.contact,
            'email': site.email,
            'name': site.name,
            'phone': site.phone,
            'site_type': site.site_type,
        }


def includeme(config):
    config.add_route(pattern='sites/{site_id}/', name='api-sites-read', factory=Sites)
