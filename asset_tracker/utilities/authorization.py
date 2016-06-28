from collections import namedtuple

from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.compat import is_nonstr_iter
from pyramid.events import NewResponse, subscriber
from pyramid.location import lineage
from pyramid.security import ACLAllowed, ACLDenied, Allow, Authenticated, Everyone
from pyramid.settings import asbool


Right = namedtuple('Right', ['tenant', 'name'])


def rights_without_tenants(principals):
    rights = set()
    for principal in principals:
        if isinstance(principal, Right):
            rights.add(principal.name)
        else:
            rights.add(principal)
    return rights


@subscriber(NewResponse)
def add_security_headers(event):
    secure_headers = asbool(event.request.registry.settings.get('asset_tracker.dev.secure_headers', True))
    if secure_headers:
        event.response.headers.add('X-Frame-Options', 'deny')
        event.response.headers.add('X-XSS-Protection', '1; mode=block')
        event.response.headers.add('X-Content-Type-Options', 'nosniff')


def get_user(request):
    return request.session.get('user')


def get_user_locale(request):
    if request.user:
        return request.user['locale']


# noinspection PyUnusedLocal
def get_effective_principals(userid, request):
    if request.user:
        if request.user['is_admin']:
            return ['g:admin']
        else:
            return [Right(tenant=item[0], name=item[1]) for item in request.user['rights']]


class RTAAuthenticationPolicy(AuthTktAuthenticationPolicy):
    # Based on Pyramid 1.6b3
    def effective_principals(self, request):
        effective_principals = [Everyone]
        userid = self.unauthenticated_userid(request)

        if userid is None:
            return effective_principals

        if self._clean_principal(userid) is None:
            return effective_principals

        if self.callback is None:
            groups = []
        else:
            groups = self.callback(userid, request)

        if groups is None:
            return effective_principals

        effective_principals.append(Authenticated)
        effective_principals.append('userid:' + userid)
        effective_principals.extend(groups)

        return effective_principals

    def unauthenticated_userid(self, request):
        try:
            return request.user['id']
        except (KeyError, TypeError):
            pass


class TenantedAuthorizationPolicy(ACLAuthorizationPolicy):
    # Based on Pyramid 1.6b3
    def permits(self, context, principals, permission):
        acl = '<No ACL found on any object in resource lineage>'

        for location in lineage(context):
            try:
                acl = location.__acl__
            except AttributeError:
                continue

            if acl and callable(acl):
                acl = acl()

            for ace in acl:
                ace_action, ace_tenant, ace_principal, ace_permissions = ace
                if (ace_tenant is None and ace_principal in rights_without_tenants(principals)) or \
                        Right(tenant=ace_tenant, name=ace_principal) in principals:
                    if not is_nonstr_iter(ace_permissions):
                        ace_permissions = [ace_permissions]
                    if permission in ace_permissions:
                        if ace_action == Allow:
                            return ACLAllowed(ace, acl, permission,
                                              principals, location)
                        else:
                            return ACLDenied(ace, acl, permission,
                                             principals, location)

        return ACLDenied('<default deny>', acl, permission, principals, context)
