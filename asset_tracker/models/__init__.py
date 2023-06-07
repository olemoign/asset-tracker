import zope.sqlalchemy
from sqlalchemy import engine_from_config
from sqlalchemy.orm import configure_mappers, sessionmaker

# import or define all models here to ensure they are attached to the
# Base.metadata prior to any initialization routines
from asset_tracker.models.asset_tracker import Asset, Consumable, ConsumableFamily, Equipment, EquipmentFamily, Event, \
    EventStatus, Site, Tenant, consumable_families_equipment_families

_ = (
    Asset, consumable_families_equipment_families, Consumable, ConsumableFamily, Equipment, EquipmentFamily, Event,
    EventStatus, Site, Tenant,
)

# run configure_mappers after defining all of the models to ensure
# all relationships can be setup
configure_mappers()


def get_engine(settings, prefix='sqlalchemy.'):
    if settings['sqlalchemy.url'].startswith('sqlite'):
        connect_args = {}
    else:
        connect_args = {'options': '-c statement_timeout=10000'}
    return engine_from_config(settings, prefix, connect_args=connect_args)


def get_session_factory(engine):
    return sessionmaker(bind=engine)


def get_tm_session(session_factory, transaction_manager):
    """Get a ``sqlalchemy.orm.Session`` instance backed by a transaction.

    This function will hook the session to the transaction manager which
    will take care of committing any changes.

    - When using pyramid_tm it will automatically be committed or aborted
      depending on whether an exception is raised.

    - When using scripts you should wrap the session in a manager yourself.
      For example::

          import transaction

          engine = get_engine(settings)
          session_factory = get_session_factory(engine)
          with transaction.manager:
              db_session = get_tm_session(session_factory, transaction.manager)
    """
    db_session = session_factory()
    zope.sqlalchemy.register(db_session, transaction_manager=transaction_manager)
    return db_session


def includeme(config):
    """Initialize the model for a Pyramid app."""
    settings = config.get_settings()
    settings['tm.manager_hook'] = 'pyramid_tm.explicit_manager'

    # use pyramid_tm to hook the transaction lifecycle to the request
    config.include('pyramid_tm')

    session_factory = get_session_factory(get_engine(settings))
    config.registry['db_session_factory'] = session_factory

    # make request.db_session available for use in Pyramid
    config.add_request_method(
        # r.tm is the transaction manager used by pyramid_tm
        lambda r: get_tm_session(session_factory, r.tm),
        'db_session',
        reify=True,
    )
