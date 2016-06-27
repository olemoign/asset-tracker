from celery.utils.log import get_task_logger
from requests import ConnectionError, HTTPError, post, Timeout

from . import app


logger = get_task_logger(__name__)


@app.task(bind=True)
def post_notifications_to_rta(self, server_url, client_id, secret, json):
    try:
        post(server_url, auth=(client_id, secret), json=json)
    except (ConnectionError, HTTPError, Timeout) as exc:
        logger.info('RTA notification failed: {}.'.format(exc))
        self.retry(countdown=30, exc=exc, max_retries=5)
