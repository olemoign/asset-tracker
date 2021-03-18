"""Equipments families and assets statuses config.

These functions are run during each function startup to make sure families and statuses in the db are up to date with
the content of config.json.
"""
import json
import logging

import importlib_resources
import transaction

from asset_tracker.models import Asset, Consumable, ConsumableFamily, Equipment, EquipmentFamily, EventStatus, \
    get_engine, get_session_factory, get_tm_session

DEFAULT_CONFIG = {
    'asset_tracker.cloud_name': 'Parsys Cloud',
    'asset_tracker.config': 'parsys',
}

MANDATORY_CONFIG = [
    'asset_tracker.blobstore_path',
    'asset_tracker.sessions_broker_url',
    'sqlalchemy.url',
    'rta.client_id',
    'rta.secret',
    'rta.server_url',
]

logger = logging.getLogger('asset_tracker_actions')


def update_consumable_families(db_session, config):
    """Update consumable families in the db according to config.json.

    Args:
        db_session (sqlalchemy.orm.session.Session).
        config (dict).
    """
    config_families = config['consumable_families']
    db_families = db_session.query(ConsumableFamily).all()

    # Remove existing family if it was removed from the config and no consumable is from this family.
    for db_family in db_families:
        config_family = next((x for x in config_families if x['family_id'] == db_family.family_id), None)

        if not config_family:
            consumable = db_session.query(Consumable).filter_by(family=db_family).first()
            if consumable:
                logger.info(
                    f'Consumable family {db_family.model} was removed from the config but can\'t be removed from the'
                    f' db.'
                )
            else:
                db_session.delete(db_family)
                logger.info(f'Deleting consumable family {db_family.model}.')

    # Create new families and update names.
    for config_family in config_families:
        db_family = next((x for x in db_families if x.family_id == config_family['family_id']), None)

        if not db_family:
            db_family = ConsumableFamily(family_id=config_family['family_id'])
            db_session.add(db_family)
            logger.info(f'Adding consumable family {config_family["model"]}.')

        db_family.model = config_family['model']

        # Update equipment family / consumable family association.
        db_family.equipment_families = []
        for equipment_family_id in config_family['equipment_family_ids']:
            equipment_family = db_session.query(EquipmentFamily).filter_by(family_id=equipment_family_id).first()
            db_family.equipment_families.append(equipment_family)


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
                logger.info(
                    f'Equipment family {db_family.model} was removed from the config but can\'t be removed from the db.'
                )
            else:
                db_session.delete(db_family)
                logger.info(f'Deleting equipment family {db_family.model}.')

    # Create new families and update names.
    for config_family in config_families:
        db_family = next((x for x in db_families if x.family_id == config_family['family_id']), None)

        if not db_family:
            db_family = EquipmentFamily(family_id=config_family['family_id'])
            db_session.add(db_family)
            logger.info(f'Adding equipment family {config_family["model"]}.')

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
                logger.info(f'Status {db_status.label} was removed from the config but can\'t be removed from the db.')
            else:
                db_session.delete(db_status)
                logger.info(f'Deleting status {db_status.label}.')

    # Create new status and update names.
    for config_status in config_statuses:
        db_status = next((x for x in db_statuses if x.status_id == config_status['status_id']), None)

        if not db_status:
            db_status = EventStatus(status_id=config_status['status_id'])
            db_session.add(db_status)
            logger.info(f'Adding status {config_status["label"]}.')

        db_status.position = int(config_status['position'])
        db_status._label = config_status['label']
        db_status._label_marlink = config_status.get('label_marlink')
        db_status.status_type = config_status['status_type']


def update_configuration(settings):
    """Run the update."""
    with transaction.manager:
        # Connect to the db.
        engine = get_engine(settings)
        db_session_factory = get_session_factory(engine)
        db_session = get_tm_session(db_session_factory, transaction.manager)

        # Read config.json.
        config_path = importlib_resources.files(__package__).joinpath('config.json')
        with open(config_path) as config_file:
            config = json.load(config_file)

        update_equipment_families(db_session, config)
        update_consumable_families(db_session, config)
        update_statuses(db_session, config)
