from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.compat import is_nonstr_iter
from pyramid.location import lineage
from pyramid.security import ACLAllowed, ACLDenied, Allow, Authenticated, Everyone


def rights_without_tenants(principals):
    rights = set()
    for principal in principals:
        if isinstance(principal, tuple):
            rights.add(principal[1])
        else:
            rights.add(principal)
    return rights


class RTAAuthenticationPolicy(AuthTktAuthenticationPolicy):
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


class TenantedAuthorizationPolicy(ACLAuthorizationPolicy):
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
                        ((ace_tenant, ace_principal) in principals):
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
