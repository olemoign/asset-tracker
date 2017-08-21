from dateutil.relativedelta import relativedelta
from parsys_utilities.model import CreationDateTimeMixin, Model
from parsys_utilities.random import random_id
from sqlalchemy import Boolean, Date, DateTime, Column, ForeignKey, Integer, Unicode as String
from sqlalchemy.orm import relationship

from asset_tracker.constants import WARRANTY_DURATION_YEARS


class Asset(Model, CreationDateTimeMixin):
    tenant_id = Column(String, nullable=False)
    asset_id = Column(String, nullable=False)
    asset_type = Column(String, nullable=False)

    customer_id = Column(String)
    customer_name = Column(String)

    site = Column(String)
    current_location = Column(String)
    notes = Column(String)

    software_version = Column(String)
    equipments = relationship('Equipment')

    _history = relationship('Event', foreign_keys='Event.asset_id', lazy='dynamic')

    def history(self, order):
        """Filter removed events from history."""
        if order == 'asc':
            return self._history.filter_by(removed=False).order_by(Event.date, Event.created_at)
        else:
            return self._history.filter_by(removed=False).order_by(Event.date.desc(), Event.created_at.desc())

    status_id = Column(Integer, ForeignKey('event_status.id'))
    status = relationship('EventStatus', foreign_keys=status_id, uselist=False)

    calibration_frequency = Column(Integer)
    calibration_next = Column(Date)

    @property
    def activation_first(self):
        """Get the date of the asset first activation."""
        activation_first = self.history('asc').join(EventStatus).filter(EventStatus.status_id == 'service').first()
        if activation_first:
            return activation_first.date

    @property
    def calibration_last(self):
        """Get the date of the asset last calibration."""
        calibration_last = self.history('desc').join(EventStatus).filter(EventStatus.status_id == 'calibration').first()
        if self.production and calibration_last:
            return max(self.production, calibration_last.date)
        # In the weird case that the asset has been calibrated but the 'stock' status has been forgotten.
        elif calibration_last:
            return calibration_last.date
        elif self.production:
            return self.production

    @property
    def production(self):
        """Get the date of the asset production."""
        production = self.history('asc').join(EventStatus).filter(EventStatus.status_id == 'stock_parsys').first()
        if production:
            return production.date

    @property
    def warranty_end(self):
        """Get the date of the end of the asset warranty."""
        if self.activation_first:
            return self.activation_first + relativedelta(years=WARRANTY_DURATION_YEARS)


class Equipment(Model):
    family_id = Column(Integer, ForeignKey('equipment_family.id'), nullable=False)
    family = relationship('EquipmentFamily', foreign_keys=family_id, uselist=False)

    asset_id = Column(Integer, ForeignKey('asset.id'), nullable=False)

    serial_number = Column(String)


class EquipmentFamily(Model):
    family_id = Column(String, nullable=False, unique=True)
    model = Column(String, nullable=False, unique=True)


class Event(Model, CreationDateTimeMixin):
    event_id = Column(String, nullable=False, unique=True, default=random_id)

    asset_id = Column(Integer, ForeignKey('asset.id'), nullable=False)

    date = Column(Date, nullable=False)

    creator_id = Column(String, nullable=False)
    creator_alias = Column(String, nullable=False)

    removed = Column(Boolean, nullable=False, default=False)
    removed_at = Column(DateTime)
    remover_id = Column(String)
    remover_alias = Column(String)

    status_id = Column(Integer, ForeignKey('event_status.id'), nullable=False)
    status = relationship('EventStatus', foreign_keys=status_id, uselist=False)


class EventStatus(Model):
    status_id = Column(String, nullable=False, unique=True)
    position = Column(Integer, nullable=False, unique=True)
    label = Column(String, nullable=False, unique=True)
