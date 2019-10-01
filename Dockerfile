FROM parsys/python-redis-supervisord

# This fix an annoying bug between python3 and ubuntu.
ENV LANG C.UTF-8

COPY dist/ /opt

# Install app.
RUN pip3 install -q --ignore-installed /opt/* \
 && mkdir -p /opt/files

# Copy config files.
COPY production.ini /opt/files
COPY supervisord.conf /opt/files
COPY alembic /opt/alembic

WORKDIR /srv

CMD mkdir -p /srv/log/ /srv/log/celery/ /srv/log/nginx/ /srv/log/supervisor/ \
 && mkdir -p /srv/socket/ /srv/data/ \
 && cp -n /opt/files/* /srv || true \
 && alembic -c /srv/production.ini upgrade head \
 && supervisord -n -c /srv/supervisord.conf
