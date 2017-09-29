from json import loads

from dateutil.relativedelta import relativedelta
from parsys_utilities.model import CreationDateTimeMixin, Model
from parsys_utilities.random import random_id
from parsys_utilities.sentry import sentry_capture_exception
from sqlalchemy import Boolean, Date, DateTime, Column, ForeignKey, Integer, Unicode as String
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property

from asset_tracker.constants import WARRANTY_DURATION_YEARS


class Asset(Model, CreationDateTimeMixin):
    tenant_id = Column(String, nullable=False)
    asset_id = Column(String, nullable=False)
    asset_type = Column(String, nullable=False)

    user_id = Column(String)  # received from RTA when create/edit station

    @property
    def is_linked(self):
        """Asset is_linked if it received user_id from RTA."""
        return bool(self.user_id)

    customer_id = Column(String)
    customer_name = Column(String)

    site_id = Column(Integer, ForeignKey('site.id'))
    site = relationship('Site', foreign_keys=site_id, uselist=False)

    current_location = Column(String)
    notes = Column(String)

    equipments = relationship('Equipment')

    _history = relationship('Event', foreign_keys='Event.asset_id', lazy='dynamic')

    def history(self, order, filter_software=False):
        """Filter removed events from history.

        Args:
            order (str): asc/desc.
            filter_software (bool): should we get software update or not ?

        """
        if order == 'asc':
            history = self._history.filter_by(removed=False).order_by(Event.date, Event.created_at)
        else:
            history = self._history.filter_by(removed=False).order_by(Event.date.desc(), Event.created_at.desc())

        if filter_software:
            history = history.join(EventStatus).filter(EventStatus.status_id != 'software_update')

        return history

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
    family_id = Column(Integer, ForeignKey('equipment_family.id'))
    family = relationship('EquipmentFamily', foreign_keys=family_id, uselist=False)

    asset_id = Column(Integer, ForeignKey('asset.id'), nullable=False)

    serial_number = Column(String)

    expiration_date_1 = Column(Date)
    expiration_date_2 = Column(Date)


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

    extra = Column(String)

    @hybrid_property
    def extra_json(self):
        """Return dictionary from extra."""
        try:
            return loads(self.extra)
        except TypeError:
            sentry_capture_exception(self.request, get_tb=True, level='info')
            return {}


class EventStatus(Model):
    status_id = Column(String, nullable=False, unique=True)
    position = Column(Integer, nullable=False, unique=True)
    label = Column(String, nullable=False, unique=True)


class Site(Model, CreationDateTimeMixin):
    tenant_id = Column(String, nullable=False)
    name = Column(String, nullable=False, unique=True)
    site_type = Column(String)

    contact = Column(String)
    phone = Column(String)
    email = Column(String)
