from pyramid.settings import asbool

from ..celery.tasks import post_notifications_to_rta


class Notifier(object):
    def __init__(self, request):
        self.request = request
        self.debug = asbool(self.request.registry.settings.get('parsys_cloud.debug'))

    def notify(self, message, user_id=None, profile=None, right=None, level='info'):
        client_id = self.request.registry.settings['rta.client_id']
        secret = self.request.registry.settings['rta.secret']
        notifications_url = self.request.route_url('rta', path='api/notifications/')

        sender_tenant = self.request.user['main_tenant'] if self.request.user else None
        json = {'message': message, 'level': level, 'sender_tenant': sender_tenant}
        if user_id:
            json.update({'user_id': user_id})
        elif profile:
            json.update({'profile': profile})
        elif right:
            json.update({'right': right})

        if not self.debug:
            args = [notifications_url, client_id, secret, json]
            post_notifications_to_rta.apply_async(args=args, queue='notifications')
