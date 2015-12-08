# -*- coding: utf-8 -*-
from logging import getLogger

from pyramid.httpexceptions import HTTPBadRequest, HTTPForbidden, HTTPFound
from pyramid.security import forget, remember
from pyramid.view import forbidden_view_config, view_config

from .openid_connect import OpenIDConnectClient

logger = getLogger('asset_tracker')


class Users(object):
    def __init__(self, request):
        self.request = request

        oauth_client_id = self.request.registry.settings['rta.client_id']
        secret = self.request.registry.settings['rta.secret']
        cookie_signature = self.request.registry.settings['asset_tracker.cookie_signature']
        self.openid_client = OpenIDConnectClient(oauth_client_id, secret, cookie_signature)

    def request_user_info_with_json_web_token(self, json_web_token, target_path):
        access_token, refresh_token, expires_in = self.openid_client.verify_json_web_token(json_web_token)

        rta_userinfo_url = self.request.route_url('rta', path='api/oauth/userinfo/')
        user_info = self.openid_client.request_user_info(rta_userinfo_url, access_token)

        self.request.session['user'] = user_info
        headers = remember(self.request, self.request.user['login'])
        response = HTTPFound(location=target_path, headers=headers)
        self.openid_client.set_cookies(response, access_token, refresh_token, expires_in)

        logger.info(';'.join([str(self.request.user['id']), 'log in']))
        return response

    @forbidden_view_config()
    def manage_forbidden(self):
        if self.request.user:
            return HTTPForbidden()
        else:
            # If an access token is present, try to retrieve the user info
            access_token = self.openid_client.read_access_token(self.request.cookies)
            if access_token:
                rta_userinfo_url = self.request.route_url('rta', path='api/oauth/userinfo/')
                try:
                    user_info = self.openid_client.request_user_info(rta_userinfo_url, access_token)
                except HTTPBadRequest:
                    user_info = None

                if user_info:
                    self.request.session['user'] = user_info
                    headers = remember(self.request, self.request.user['login'])
                    logger.info(';'.join([str(self.request.user['id']), 'log in']))
                    return HTTPFound(location=self.request.path, headers=headers)

            # If no access token was present or the token was bad, but we have a refresh token, use it
            refresh_token = self.openid_client.read_refresh_token(self.request.cookies)
            if refresh_token:
                rta_token_url = self.request.route_url('rta', path='api/oauth/token/')
                try:
                    json_web_token = self.openid_client.request_access_token_with_refresh_token(rta_token_url, refresh_token)
                except HTTPBadRequest:
                    json_web_token = None

                if json_web_token:
                    return self.request_user_info_with_json_web_token(json_web_token, self.request.path)

            # If we had neither an access or refresh token, go through the whole Oauth2 process
            request_token_endpoint = self.request.route_url('oauth_request_token')
            rta_authorization_url = self.request.route_url('rta', path='api/oauth/authorize/')
            csrf_token = self.request.session.new_csrf_token()

            rta_authorization_request = self.openid_client.request_user_authentication(rta_authorization_url, request_token_endpoint, csrf_token, self.request.path)

            response = HTTPFound(location=rta_authorization_request)
            self.openid_client.delete_cookies(response)
            return response

    @view_config(route_name='oauth_request_token', request_method='GET')
    def request_token(self):
        session_csrf_token = self.request.session.get_csrf_token()
        authorization_code, user_target_path = self.openid_client.verify_authorization_response(self.request.url, session_csrf_token)

        if authorization_code:
            rta_token_url = self.request.route_url('rta', path='api/oauth/token/')
            request_token_endpoint = self.request.route_url('oauth_request_token')
            json_web_token = self.openid_client.request_access_token_with_authorization_code(rta_token_url, authorization_code, request_token_endpoint)

            return self.request_user_info_with_json_web_token(json_web_token, user_target_path)

    @view_config(route_name='users_logout', request_method='GET', permission='authenticated')
    def logout_get(self):
        # TODO
        rta_logout_url = self.request.route_url('rta', path='users/logout/')
        response = HTTPFound(location=rta_logout_url, headers=forget(self.request))
        self.openid_client.delete_cookies(response)
        self.request.session.invalidate()

        logger.info(';'.join([str(self.request.user['id']), 'log out']))
        return response


def includeme(config):
    config.add_route(pattern='users/logout/',               name='users_logout')
    config.add_route(pattern='oauth/request_token/',        name='oauth_request_token')