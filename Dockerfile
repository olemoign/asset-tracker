FROM python:3

# should not copy this in a layer. Maybe use a wheel cache outside ? or a local bind ?
COPY dist/ /opt

# Install app, supervisor
RUN pip -q install /opt/* \
 && mkdir -p /opt/files

# copy config files
COPY production.ini /opt/files
WORKDIR /srv


CMD mkdir -p /srv/log/ /srv/socket/ /srv/data/ \
 && cp -n /opt/files/* /srv || true \
 && pserve production.ini
