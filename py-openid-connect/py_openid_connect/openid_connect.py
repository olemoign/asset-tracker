from urllib.parse import parse_qs, quote, unquote, urlencode

from jwt import decode, ExpiredSignatureError, InvalidAudienceError, InvalidIssuerError
from oauthlib.oauth2 import OAuth2Error, WebApplicationClient
from pyramid.httpexceptions import HTTPBadRequest, HTTPUnauthorized, HTTPServiceUnavailable
from pyramid.session import signed_deserialize, signed_serialize
from pyramid.settings import asbool
from requests import ConnectionError, Timeout, get, post


class OpenIDConnectClient(object):
    def __init__(self, oauth_client_id, secret, cookie_signature):
        self.oauth_client_id = oauth_client_id
        self.oauth_client = WebApplicationClient(oauth_client_id)
        self.secret = secret
        self.cookie_signature = cookie_signature

    @staticmethod
    def delete_cookies(response):
        response.delete_cookie('rta_at')
        response.delete_cookie('rta_rt')

    @staticmethod
    def persistant_cookies(request):
        return request.cookies.get('rta_persist')

    def read_access_token(self, cookies):
        if cookies.get('rta_at'):
            try:
                access_token = signed_deserialize(cookies['rta_at'], self.cookie_signature)
            except ValueError:
                pass
            else:
                return access_token

    def read_refresh_token(self, cookies):
        if cookies.get('rta_rt'):
            try:
                refresh_token = signed_deserialize(cookies['rta_rt'], self.cookie_signature)
            except ValueError:
                pass
            else:
                return refresh_token

    def request_access_token_with_authorization_code(self, url, authorization_code, client_redirect_endpoint):
        # Using authorization code, request token.
        data = self.oauth_client.prepare_request_body(code=authorization_code, redirect_uri=client_redirect_endpoint)
        try:
            response = post(url, data=data, auth=(self.oauth_client_id, self.secret))
        except (ConnectionError, Timeout):
            raise HTTPServiceUnavailable()

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 400:
            raise HTTPBadRequest()
        else:
            raise HTTPServiceUnavailable()

    def request_access_token_with_refresh_token(self, url, refresh_token):
        # Access token has expired but we have a refresh token, request new access token using the refresh token.
        data = self.oauth_client.prepare_refresh_body(refresh_token=refresh_token)
        try:
            response = post(url, data=data, auth=(self.oauth_client_id, self.secret))
        except (ConnectionError, Timeout):
            raise HTTPServiceUnavailable()

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 400:
            raise HTTPBadRequest()
        elif response.status_code in {401, 403}:
            raise HTTPUnauthorized()
        else:
            raise HTTPServiceUnavailable()

    def request_user_authentication(self, url, client_redirect_endpoint, csrf_token, user_target_path):
        state = {'csrf_token': csrf_token, 'target_path': user_target_path}
        encoded_state = quote(urlencode(state))

        rta_authorization_request = self.oauth_client.prepare_request_uri(
            url, scope=['openid'], redirect_uri=client_redirect_endpoint, state=encoded_state)

        return rta_authorization_request

    def set_cookies(self, response, access_token, refresh_token, expires_in):
        response.set_cookie('rta_at', signed_serialize(access_token, self.cookie_signature), max_age=expires_in)
        if expires_in:
            rt_max_age = 604800
            response.set_cookie('rta_persist', signed_serialize('True', self.cookie_signature), max_age=rt_max_age)
        else:
            rt_max_age = None
        response.set_cookie('rta_rt', signed_serialize(refresh_token, self.cookie_signature), max_age=rt_max_age)

    @staticmethod
    def request_user_info(url, access_token):
        try:
            response = get(url, headers={'authorization': 'Bearer ' + access_token})
        except (ConnectionError, Timeout):
            raise HTTPServiceUnavailable()

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 400:
            raise HTTPBadRequest()
        elif response.status_code in {401, 403}:
            raise HTTPUnauthorized()
        else:
            raise HTTPServiceUnavailable()

    def verify_authorization_response(self, url, session_csrf_token):
        try:
            # Retrieve information from Oauth authorization success
            authorization_response = self.oauth_client.parse_request_uri_response(url)
            authorization_code = authorization_response['code']
            state_encoded = authorization_response['state']
            state = parse_qs(unquote(state_encoded))

            csrf_token = state['csrf_token'][0]
            user_target_path = state['target_path'][0]
            # TODO-OLM
            persist = parse_qs(url).get('persist')
            persist = asbool(persist[0]) if persist else False
        except (IndexError, KeyError, TypeError):
            raise HTTPBadRequest()

        if csrf_token == session_csrf_token:
            return authorization_code, persist, user_target_path
        else:
            raise HTTPBadRequest()

    def verify_json_web_token(self, jwt):
        try:
            signed_id_token = jwt['id_token']
            access_token = jwt['access_token']
            refresh_token = jwt['refresh_token']
            expires_in = int(jwt['expires_in'])
        except (KeyError, TypeError):
            raise HTTPBadRequest()

        try:
            # Even if we don't persist it, make sure that the id_token is valid
            # TODO-OLM: issuer
            _ = decode(signed_id_token, self.secret, audience=self.oauth_client_id)
        except (ExpiredSignatureError, InvalidAudienceError, InvalidIssuerError, OAuth2Error):
            return HTTPBadRequest()
        else:
            return access_token, refresh_token, expires_in
