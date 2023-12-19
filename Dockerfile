FROM tracker.parsys.com:1337/parsys/docker-files:python AS python_source
# Copy wheels.
COPY dist/ /opt

FROM tracker.parsys.com:1337/parsys/docker-files:python
# Install wheels.
RUN --mount=type=bind,from=python_source,source=/opt,target=/opt pip3 install --no-cache-dir --no-compile /opt/*

# Copy config files.
COPY docker-compose.yml /opt
COPY config/production.ini /opt
COPY alembic /opt/alembic
COPY docker-entrypoint.sh /usr/local/bin

ENTRYPOINT ["docker-entrypoint.sh"]

CMD ["pserve", "/srv/production.ini"]
