FROM tracker.parsys.com:1337/parsys/docker-files:python

# This fix an annoying bug between python3 and ubuntu.
ENV LANG C.UTF-8

COPY dist/ /opt

# Install app.
RUN pip3 install -q --no-cache-dir --ignore-installed --use-deprecated=legacy-resolver /opt/*
RUN rm /opt/*

# Copy config files.
COPY docker-compose.yml /opt
COPY config/production.ini /opt
COPY alembic /opt/alembic

COPY docker-entrypoint.sh /usr/local/bin
ENTRYPOINT ["docker-entrypoint.sh"]

CMD ["pserve", "/srv/production.ini"]
