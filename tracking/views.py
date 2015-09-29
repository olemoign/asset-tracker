from codecs import encode
from logging import getLogger
from os import urandom
from urllib.parse import parse_qs, quote, unquote, urlencode

from jwt import decode, ExpiredSignatureError, InvalidAudienceError, InvalidIssuerError
from requests import ConnectionError, get, post, Timeout
from oauthlib.oauth2 import OAuth2Error, WebApplicationClient

from pyramid.httpexceptions import HTTPBadRequest, HTTPForbidden, HTTPFound, HTTPServiceUnavailable
from pyramid.security import Allow, Authenticated, forget, remember
from pyramid.session import signed_deserialize, signed_serialize
from pyramid.view import forbidden_view_config, view_config

logger = getLogger('tracking')


class AssetsEndPoint(object):
    __acl__ = [
        (Allow, 'r:assets-create', 'assets-create'),
        (Allow, 'r:assets-update', 'assets-update'),
        (Allow, 'r:assets-list', 'assets-list'),
    ]

    def __init__(self, request):
        self.request = request

    @view_config(route_name='assets-create', request_method='GET', permission='assets-create', renderer='assets-create_update.html')
    def create_get(self):
        return {}

    @view_config(route_name='assets-create', request_method='POST', permission='assets-create', renderer='assets-create_update.html')
    def create_post(self):
        return {}

    @view_config(route_name='assets-update', request_method='GET', permission='assets-update', renderer='assets-create_update.html')
    def update_get(self):
        return {}

    @view_config(route_name='assets-update', request_method='POST', permission='assets-update', renderer='assets-create_update.html')
    def update_post(self):
        return {}

    @view_config(route_name='assets-list', request_method='GET', permission='assets-list', renderer='assets-list.html')
    def list_get(self):
        return {}


class Users(object):
    def __init__(self, request):
        self.request = request

    @forbidden_view_config()
    def manage_forbidden(self):
        if self.request.user:
            return HTTPForbidden()
        else:
            if self.request.cookies.get('rta_at'):
                # Access token is still valid, request user info using access token
                cookie_signature = self.request.registry.settings.get('meerkat.cookie_signature')
                try:
                    access_token = signed_deserialize(self.request.cookies.get('rta_at'), cookie_signature)
                except ValueError:
                    access_token = None

                if access_token:
                    try:
                        user_info = self.oauth2_request_user_info(access_token)
                    except (ConnectionError, Timeout):
                        return HTTPServiceUnavailable()

                    if user_info:
                        self.request.session['user'] = user_info
                        self.request.user = user_info
                        headers = remember(self.request, self.request.user['id'])
                        logger.info(';'.join([str(self.request.user['id']), 'log in']))
                        return HTTPFound(location=self.request.path, headers=headers)

            if self.request.cookies.get('rta_rt'):
                # Access token has expired but we have a refresh token, request new access token using the refresh token
                cookie_signature = self.request.registry.settings.get('meerkat.cookie_signature')
                try:
                    refresh_token = signed_deserialize(self.request.cookies.get('rta_rt'), cookie_signature)
                except ValueError:
                    refresh_token = None

                if refresh_token:
                    oauth_client_id = self.request.registry.settings['rta.client_id']
                    oauth_client = WebApplicationClient(oauth_client_id)
                    rta_token_url = self.request.route_url('rta', path='api/oauth/token/')
                    data = oauth_client.prepare_refresh_body(refresh_token=refresh_token)
                    secret = self.request.registry.settings['rta.secret']
                    try:
                        r = post(rta_token_url, data=data, auth=(oauth_client_id, secret))
                    except (ConnectionError, Timeout):
                        return HTTPServiceUnavailable()

                    return self.oauth2_manage_access_token(r, self.request.path)

            # Either access token and refresh tokens failed or no existing authentication information => prepare OAuth authorization process
            oauth_client_id = self.request.registry.settings['rta.client_id']
            oauth_client = WebApplicationClient(oauth_client_id)
            meerkat_request_token_endpoint = self.request.route_url('oauth_request_token')
            rta_authorization_url = self.request.route_url('rta', path='api/oauth/authorize/')

            security_token = encode(urandom(16), 'hex_codec').decode('utf-8')
            target_path = self.request.path
            state = {'security_token': security_token, 'target_path': target_path}
            rta_authorization_request = oauth_client.prepare_request_uri(rta_authorization_url, redirect_uri=meerkat_request_token_endpoint, state=quote(urlencode(state)))

            self.request.session['rta_csrf'] = security_token
            return HTTPFound(location=rta_authorization_request)

    @view_config(route_name='oauth-request_token', request_method='GET')
    def request_token(self):
        oauth_client_id = self.request.registry.settings['rta.client_id']
        oauth_client = WebApplicationClient(oauth_client_id)
        try:
            # Retrieve information from Oauth authorization success
            authorization_response = oauth_client.parse_request_uri_response(self.request.url)
            authorization_code = authorization_response['code']
            state_encoded = authorization_response['state']
            state = parse_qs(unquote(state_encoded))

            security_token = state['security_token'][0]
            target_path = state['target_path'][0]
        except (IndexError, KeyError, TypeError):
            return HTTPBadRequest()

        if security_token and security_token == self.request.session.pop('rta_csrf', None):
            # Using authorization code, request token
            rta_token_url = self.request.route_url('rta', path='api/oauth/token/')
            data = oauth_client.prepare_request_body(code=authorization_code, redirect_uri=self.request.route_url('oauth_request_token'))
            secret = self.request.registry.settings['rta.secret']
            try:
                r = post(rta_token_url, data=data, auth=(oauth_client_id, secret))
            except (ConnectionError, Timeout):
                return HTTPServiceUnavailable()

            return self.oauth2_manage_access_token(r, target_path)

        return HTTPBadRequest()

    def oauth2_request_user_info(self, access_token):
        rta_userinfo_url = self.request.route_url('rta', path='api/oauth/userinfo/')
        r = get(rta_userinfo_url, params={'access_token': access_token})
        if r.status_code == 200:
            return r.json()
        else:
            return None

    def oauth2_manage_access_token(self, r, target_path):
        try:
            response_json = r.json()
            signed_id_token = response_json['id_token']
            access_token = response_json['access_token']
            refresh_token = response_json['refresh_token']
            expires_in = int(response_json['expires_in'])
        except (KeyError, TypeError, ValueError):
            return HTTPBadRequest()

        audience = self.request.registry.settings['rta.client_id']
        secret = self.request.registry.settings['rta.secret']
        try:
            # Even if we don't persist it, make sure that the id_token is valid
            id_token = decode(signed_id_token, secret, audience=audience)
        except (ExpiredSignatureError, InvalidAudienceError, InvalidIssuerError, OAuth2Error):
            return HTTPBadRequest()

        # Using access token, request user info
        try:
            user_info = self.oauth2_request_user_info(access_token)
        except (ConnectionError, Timeout):
            return HTTPServiceUnavailable()

        # If Oauth server returned user info, persist everything
        if user_info:
            self.request.session['user'] = user_info
            self.request.user = user_info
            headers = remember(self.request, self.request.user['id'])
            response = HTTPFound(location=target_path, headers=headers)
            cookie_signature = self.request.registry.settings['tracking.cookie_signature']
            response.set_cookie('rta_at', signed_serialize(access_token, cookie_signature), max_age=expires_in)
            response.set_cookie('rta_rt', signed_serialize(refresh_token, cookie_signature), max_age=604800)
            logger.info(';'.join([str(self.request.user['id']), 'log in']))
            return response

    @view_config(route_name='users-logout', request_method='GET', permission='authenticated')
    def logout_get(self):
        client_id = self.request.registry.settings['rta.client_id']
        rta_logout_url = self.request.route_url('rta', path='users/logout/', _query=(('client_id', client_id),))
        response = HTTPFound(location=rta_logout_url, headers=forget(self.request))
        response.delete_cookie('rta_at')
        response.delete_cookie('rta_rt')
        self.request.session.invalidate()
        logger.info(';'.join([str(self.request.user['id']), 'log out']))
        return response


def includeme(config):
    config.add_route(pattern='',                        name='assets-list',             factory=AssetsEndPoint)
    config.add_route(pattern='create/',                 name='assets-create',           factory=AssetsEndPoint)
    config.add_route(pattern='{asset_id}/',             name='assets-update',           factory=AssetsEndPoint)
    config.add_route(pattern='logout/',                 name='users-logout')
    config.add_route(pattern='oauth/request_token/',    name='oauth-request_token')
