from json import loads

from dateutil.relativedelta import relativedelta
from parsys_utilities.model import CreationDateTimeMixin, Model
from parsys_utilities.random import random_id
from sqlalchemy import Boolean, Date, DateTime, Column, ForeignKey, Integer, Table, Unicode as String, UniqueConstraint
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import backref, relationship

from asset_tracker.constants import WARRANTY_DURATION_YEARS


class Asset(Model, CreationDateTimeMixin):
    tenant_id = Column(String, nullable=False)
    asset_id = Column(String, nullable=False, unique=True)
    asset_type = Column(String, nullable=False)
    hardware_version = Column(String)
    mac_wifi = Column(String)
    mac_ethernet = Column(String)

    user_id = Column(String)  # Received from RTA during station creation/update.

    @property
    def is_linked(self):
        """Asset is_linked if it received user_id from RTA."""
        return bool(self.user_id)

    customer_id = Column(String)
    customer_name = Column(String)

    site_id = Column(Integer, ForeignKey('site.id'))
    site = relationship('Site', foreign_keys=site_id, backref='assets', uselist=False)

    current_location = Column(String)
    notes = Column(String)

    def history(self, order, filter_config=False):
        """Filter removed events from history.

        Args:
            order (str): asc/desc.
            filter_config (bool): should we get config updates?
        """
        if order == 'asc':
            history = self._history.filter_by(removed=False).order_by(Event.date, Event.created_at)
        else:
            history = self._history.filter_by(removed=False).order_by(Event.date.desc(), Event.created_at.desc())

        if filter_config:
            history = history.join(Event.status).filter(EventStatus.status_type != 'config')

        return history

    status_id = Column(Integer, ForeignKey('event_status.id'))
    status = relationship('EventStatus', foreign_keys=status_id, uselist=False)

    calibration_frequency = Column(Integer)
    calibration_next = Column(Date)

    def _get_asset_dates(self):
        """Compute all the dates in one method to avoid too many sql request."""
        self._asset_dates = {}

        activation_first = self.history('asc').join(Event.status).filter(EventStatus.status_id == 'service').first()
        if activation_first:
            self._asset_dates['activation_first'] = activation_first.date
            self._asset_dates['warranty_end'] = activation_first.date + relativedelta(years=WARRANTY_DURATION_YEARS)
        else:
            self._asset_dates['activation_first'] = None
            self._asset_dates['warranty_end'] = None

        production = self.history('asc').join(Event.status).filter(EventStatus.status_id == 'stock_parsys').first()
        if production:
            self._asset_dates['production'] = production.date
        else:
            self._asset_dates['production'] = None

        calibration_last = self.history('desc').join(Event.status) \
            .filter(EventStatus.status_id == 'calibration').first()
        if production and calibration_last:
            self._asset_dates['calibration_last'] = max(production.date, calibration_last.date)
        # In the weird case that the asset has been calibrated but the 'stock' status has been forgotten.
        elif calibration_last:
            self._asset_dates['calibration_last'] = calibration_last.date
        elif production:
            self._asset_dates['calibration_last'] = production.date
        else:
            self._asset_dates['calibration_last'] = None

    @property
    def asset_dates(self):
        if not hasattr(self, '_asset_dates'):
            self._get_asset_dates()

        return self._asset_dates

    @property
    def activation_first(self):
        """Get the date of the asset first activation."""
        return self.asset_dates['activation_first']

    @property
    def calibration_last(self):
        """Get the date of the asset last calibration."""
        return self.asset_dates['calibration_last']

    @property
    def production(self):
        """Get the date of the asset production."""
        return self.asset_dates['production']

    @property
    def warranty_end(self):
        """Get the date of the end of the asset warranty."""
        return self.asset_dates['warranty_end']


class Consumable(Model):
    family_id = Column(Integer, ForeignKey('consumable_family.id'))
    family = relationship('ConsumableFamily', foreign_keys=family_id, uselist=False)

    equipment_id = Column(Integer, ForeignKey('equipment.id'), nullable=False)
    equipment = relationship('Equipment', foreign_keys=equipment_id, backref='consumables', uselist=False)

    expiration_date = Column(Date)


# Association table between consumable families and equipment families (n to n).
consumable_families_equipment_families = Table(
    'consumable_families_equipment_families',
    Model.metadata,
    Column('consumable_family_id', Integer, ForeignKey('consumable_family.id'), nullable=False),
    Column('equipment_family_id', Integer, ForeignKey('equipment_family.id'), nullable=False),
    UniqueConstraint('consumable_family_id', 'equipment_family_id'),
)


class ConsumableFamily(Model):
    family_id = Column(String, nullable=False, unique=True)
    model = Column(String, nullable=False, unique=True)
    equipment_families = relationship(
        'EquipmentFamily', secondary=consumable_families_equipment_families, backref='consumable_families'
    )


class Equipment(Model):
    family_id = Column(Integer, ForeignKey('equipment_family.id'))
    family = relationship('EquipmentFamily', foreign_keys=family_id, backref='equipments', uselist=False)

    asset_id = Column(Integer, ForeignKey('asset.id'), nullable=False)
    asset = relationship('Asset', foreign_keys=asset_id, backref='equipments', uselist=False)

    serial_number = Column(String)


class EquipmentFamily(Model):
    family_id = Column(String, nullable=False, unique=True)
    model = Column(String, nullable=False, unique=True)


class Event(Model, CreationDateTimeMixin):
    event_id = Column(String, default=random_id, nullable=False, unique=True)

    asset_id = Column(Integer, ForeignKey('asset.id'), nullable=False)
    asset = relationship('Asset', foreign_keys=asset_id, backref=backref('_history', lazy='dynamic'), uselist=False)

    date = Column(Date, nullable=False)

    creator_id = Column(String, nullable=False)
    creator_alias = Column(String, nullable=False)

    removed = Column(Boolean, nullable=False, default=False)
    removed_at = Column(DateTime)
    remover_id = Column(String)
    remover_alias = Column(String)

    status_id = Column(Integer, ForeignKey('event_status.id'), nullable=False)
    status = relationship('EventStatus', foreign_keys=status_id, uselist=False)

    extra = Column(String)

    @hybrid_property
    def extra_json(self):
        """Return dictionary from extra."""
        try:
            return loads(self.extra)
        except TypeError:
            return {}


class EventStatus(Model):
    status_id = Column(String, nullable=False, unique=True)
    position = Column(Integer, nullable=False, unique=True)
    label = Column(String, nullable=False, unique=True)
    status_type = Column(String, nullable=False)


class Site(Model, CreationDateTimeMixin):
    site_id = Column(String, default=random_id, nullable=False, unique=True)

    tenant_id = Column(String, nullable=False)
    name = Column(String, nullable=False, unique=True)
    site_type = Column(String)

    contact = Column(String)
    phone = Column(String)
    email = Column(String)
