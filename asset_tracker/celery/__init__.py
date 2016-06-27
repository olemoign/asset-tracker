from configparser import ConfigParser
from os import getcwd, path
from sys import argv

from celery import Celery

app = Celery()
app.conf.update(
    CELERY_IMPORTS=['asset_tracker.celery.tasks'],
    CELERY_TASK_SERIALIZER='json',
    CELERY_ACCEPT_CONTENT=['json'],
    CELERY_ENABLE_UTC=True,
)

if path.basename(argv[0]) == 'celery':
    ini_index = argv.index('--ini')
    argv.pop(ini_index)
    config_file = argv.pop(ini_index)

    config = ConfigParser({'here': getcwd()})
    config.read(config_file)

    broker_url = config['app:main']['celery.broker_url']
    app.conf.update(BROKER_URL=broker_url)