import logging
from json import loads

import pkg_resources
import transaction

from asset_tracker.models import Equipment, EquipmentFamily, get_engine, get_session_factory, get_tm_session, \
    EventStatus


logger = logging.getLogger('asset_tracker_actions')


def update_equipment_families(db_session, configuration):
    config_families = configuration['equipment_families']
    db_families = db_session.query(EquipmentFamily).all()

    # Create new families and update names.
    for config_family in config_families:
        db_family = next((x for x in db_families if x.family_id == config_family['family_id']), None)

        if not db_family:
            db_family = EquipmentFamily(family_id=config_family['family_id'])
            db_session.add(db_family)
            logger.info('Adding equipment family {}.'.format(config_family['model']))

        db_family.model = config_family['model']

    # Remove existing family if it was removed from the config and no equipment is from this family.
    for db_family in db_families:
        config_family = next((x for x in config_families if x['family_id'] == db_family.family_id), None)

        if not config_family:
            equipment = db_session.query(Equipment).filter_by(family=db_family).first()
            if equipment:
                message = 'Equipment family {} was removed from the configuration but can\'t be removed from the db.'
                logger.info(message.format(db_family.model))
            else:
                db_session.delete(db_family)
                logger.info('Deleting equipment family {}.'.format(db_family.model))


def update_statuses(db_session, configuration):
    config_statuses = configuration['status']
    db_statuses = db_session.query(EventStatus).all()

    # Create new status and update names.
    for config_status in config_statuses:
        db_status = next((x for x in db_statuses if x.status_id == config_status['status_id']), None)

        if not db_status:
            db_status = EventStatus(status_id=config_status['status_id'])
            db_session.add(db_status)
            logger.info('Adding status {}.'.format(config_status['label']))

        db_status.position = int(config_status['position'])
        db_status.label = config_status['label']

    # Remove existing status if it was removed from the config and no equipment ever had this status.
    for db_status in db_statuses:
        config_status = next((x for x in config_statuses if x['status_id'] == db_status.status_id), None)

        if not config_status:
            event = db_session.query(Equipment).filter_by(status=db_status).first()
            if event:
                message = 'Status {} was removed from the configuration but can\'t be removed from the db.'
                logger.info(message.format(db_status.label))
            else:
                db_session.delete(db_status)
                logger.info('Deleting status {}.'.format(db_status.label))


def update_configuration(settings):
    with transaction.manager:
        engine = get_engine(settings)
        db_session_factory = get_session_factory(engine)
        db_session = get_tm_session(db_session_factory, transaction.manager)

        configuration = pkg_resources.resource_string(__name__, 'configuration.json').decode('utf-8')
        configuration = loads(configuration)

        update_equipment_families(db_session, configuration)
        update_statuses(db_session, configuration)
