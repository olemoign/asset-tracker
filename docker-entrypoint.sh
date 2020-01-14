#!/bin/bash
set -Eeuo pipefail

mkdir -p /srv/log/ /srv/log/celery/ /srv/log/nginx/
mkdir -p /srv/data/ /srv/data/blobstore/ /srv/data/postgres/ /srv/data/redis/
cp -n /opt/docker-compose.yml /srv
cp -n /opt/production.ini /srv
alembic -c /srv/production.ini upgrade head

exec "$@"
