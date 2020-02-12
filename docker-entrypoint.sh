#!/bin/bash
set -Eeuo pipefail

celery=false
if [ "$1" == "--celery" ]
then
  celery=true
  set -- "${@:2}"
fi

if [ "$celery" == true ]
then
  mkdir -p /srv/log/ /srv/log/celery/
  mkdir -p /srv/data/ /srv/data/redis/
  cp -n /opt/production.ini /srv
else
  mkdir -p /srv/log/ /srv/log/nginx/
  mkdir -p /srv/data/ /srv/data/blobstore/ /srv/data/postgres/ /srv/data/redis/
  cp -n /opt/docker-compose.yml /srv
  cp -n /opt/production.ini /srv
  alembic -c /srv/production.ini upgrade head
fi

exec "$@"
