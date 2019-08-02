"""Equipments families and assets statuses config.

These functions are run during each function startup to make sure families and statuses in the db are up to date with
the content of config.json.

"""
import logging
from json import loads

import pkg_resources
import transaction

from asset_tracker.models import Asset, Equipment, EquipmentFamily, EventStatus, get_engine, get_session_factory, \
    get_tm_session

DEFAULT_CONFIG = {
    'asset_tracker.branding': 'parsys',
    'asset_tracker.cloud_name': 'Parsys Cloud',
}

logger = logging.getLogger('asset_tracker_actions')


def update_equipment_families(db_session, config):
    """Update equipments families in the db according to config.json.

    Args:
        db_session (sqlalchemy.orm.session.Session).
        config (dict).

    """
    config_families = config['equipment_families']
    db_families = db_session.query(EquipmentFamily).all()

    # Remove existing family if it was removed from the config and no equipment is from this family.
    for db_family in db_families:
        config_family = next((x for x in config_families if x['family_id'] == db_family.family_id), None)

        if not config_family:
            equipment = db_session.query(Equipment).filter_by(family=db_family).first()
            if equipment:
                message = 'Equipment family {} was removed from the config but can\'t be removed from the db.'
                logger.info(message.format(db_family.model))
            else:
                db_session.delete(db_family)
                logger.info('Deleting equipment family {}.'.format(db_family.model))

    # Create new families and update names.
    for config_family in config_families:
        db_family = next((x for x in db_families if x.family_id == config_family['family_id']), None)

        if not db_family:
            db_family = EquipmentFamily(family_id=config_family['family_id'])
            db_session.add(db_family)
            logger.info('Adding equipment family {}.'.format(config_family['model']))

        db_family.model = config_family['model']


def update_statuses(db_session, config):
    """Update assets statuses in the db according to config.json.

    Args:
        db_session (sqlalchemy.orm.session.Session).
        config (dict).

    """
    config_statuses = config['status']
    db_statuses = db_session.query(EventStatus).all()

    # Put temp positions to make sure we don't overwrite existing ones, as the position has to be unique.
    for index, db_status in enumerate(db_statuses):
        db_status.position = 10000 + index

    db_session.flush()

    # Remove existing status if it was removed from the config and no asset ever had this status.
    for db_status in db_statuses:
        config_status = next((x for x in config_statuses if x['status_id'] == db_status.status_id), None)

        if not config_status:
            event = db_session.query(Asset).filter_by(status=db_status).first()
            if event:
                message = 'Status {} was removed from the config but can\'t be removed from the db.'
                logger.info(message.format(db_status.label))
            else:
                db_session.delete(db_status)
                logger.info('Deleting status {}.'.format(db_status.label))

    # Create new status and update names.
    for config_status in config_statuses:
        db_status = next((x for x in db_statuses if x.status_id == config_status['status_id']), None)

        if not db_status:
            db_status = EventStatus(status_id=config_status['status_id'])
            db_session.add(db_status)
            logger.info('Adding status {}.'.format(config_status['label']))

        db_status.position = int(config_status['position'])
        db_status.label = config_status['label']


def update_configuration(settings):
    """Run the update."""
    with transaction.manager:
        # Connect to the db.
        engine = get_engine(settings)
        db_session_factory = get_session_factory(engine)
        db_session = get_tm_session(db_session_factory, transaction.manager)

        # Read config.json.
        config = pkg_resources.resource_string(__name__, 'config.json').decode('utf-8')
        config = loads(config)

        update_equipment_families(db_session, config)
        update_statuses(db_session, config)