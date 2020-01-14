FROM parsys/python

# This fix an annoying bug between python3 and ubuntu.
ENV LANG C.UTF-8

COPY dist/ /opt

# Install app.
RUN pip3 install -q --ignore-installed /opt/*
RUN rm /opt/*

# Copy config files.
COPY docker-compose.yml /opt
COPY docker-entrypoint.sh /opt
COPY config/production.ini /opt
COPY alembic /opt/alembic

ENTRYPOINT ["/opt/docker-entrypoint.sh"]

CMD ["pserve", "/srv/production.ini"]
