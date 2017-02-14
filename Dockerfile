# We use buildpack for now, will use alpine later.
FROM parsys/python2-python3-redis-supervisord

# This fix an annoying bug between python3 and ubuntu.
ENV LANG C.UTF-8

# Should not copy this in a layer. Maybe use a wheel cache outside ? or a local bind ?
COPY dist/ /opt

# Install app.
RUN pip -q install /opt/* \
 && mkdir -p /opt/files

# Copy config files.
COPY production.ini /opt/files
COPY supervisord.conf /opt/files
COPY migrations /opt/migrations

WORKDIR /srv

CMD mkdir -p /srv/log/ /srv/socket/ /srv/data/ \
 && cp -n /opt/files/* /srv || true \
 && alembic -c production.ini upgrade head \
 && supervisord -n -c /srv/supervisord.conf
