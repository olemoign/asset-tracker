from parsys_utilities.authorization import Right
from pyramid.view import view_config
from sentry_sdk import capture_message

from asset_tracker import models


class Sites:
    """(Cloud) Get site info in consultation."""

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

        # Make sure that the user get an iframe in all cases. If he doesn't have the necessary rights or even if he
        # isn't authenticated anymore (super edge case).
        principals = self.request.effective_principals
        if not principals or Right(name='api-sites-read', tenant=site.tenant_id) not in principals:
            return {}

        return {
            'contact': site.contact,
            'email': site.email,
            'name': site.name,
            'phone': site.phone,
            'site_type': site.site_type,
        }


def includeme(config):
    config.add_route(pattern=r'sites/{site_id:\w{8}}/', name='api-sites-read', factory=Sites)
