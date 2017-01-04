from dateutil.relativedelta import relativedelta
from parsys_utilities.model import and_, Boolean, CreationDateTimeMixin, DateTime, Field, ForeignKey, hybrid_method, \
    hybrid_property, Integer, join, Model, relationship, select, String
from parsys_utilities.random import random_id

from asset_tracker.constants import CALIBRATION_FREQUENCY_YEARS


class Asset(Model, CreationDateTimeMixin):
    tenant_id = Field(String, nullable=False)
    asset_id = Field(String, nullable=False)
    type = Field(String)

    customer_id = Field(String)
    customer_name = Field(String)

    site = Field(String)
    current_location = Field(String)
    notes = Field(String)

    software_version = Field(String)
    _history = relationship('Event', lazy='dynamic')
    equipments = relationship('Equipment')

    @hybrid_method
    def history(self, order):
        if order == 'asc':
            return self._history.filter_by(removed=False).order_by(Event.date, Event.created_at)
        else:
            return self._history.filter_by(removed=False).order_by(Event.date.desc(), Event.created_at.desc())

    @hybrid_property
    def status(self):
        history = self.history('desc').all()
        if history:
            return history[0].status

    # noinspection PyMethodParameters
    @status.expression
    def status(cls):
        # IMPORTANT: As this only used for ordering at the moment, return only the position instead of the full status.
        return select([EventStatus.position]).select_from(join(Event, EventStatus)) \
            .where(and_(Event.asset_id == cls.id, Event.removed == False)) \
            .order_by(Event.date.desc(), Event.created_at.desc()).limit(1)  # noqa: E712

    @hybrid_property
    def calibration_next(self):
        activation_last = self.history('desc').join(EventStatus).filter(EventStatus.status_id == 'service').first()
        if activation_last:
            return activation_last.date.date() + relativedelta(years=CALIBRATION_FREQUENCY_YEARS)

    # noinspection PyMethodParameters
    @calibration_next.expression
    def calibration_next(cls):
        # IMPORTANT: This returns the last calibration, which works as this function is used for ordering and
        # currently the delta between next and last calibration is the same for all assets.
        # This will need work if the delta is no longer the same for all.
        return select([Event.date]).select_from(join(Event, EventStatus)) \
            .where(and_(Event.asset_id == cls.id, Event.removed == False, EventStatus.status_id == 'service')) \
            .order_by(Event.date.desc(), Event.created_at.desc()).limit(1)  # noqa: E712


class Equipment(Model):
    family_id = Field(Integer, ForeignKey('equipment_family.id'))
    family = relationship('EquipmentFamily', foreign_keys=family_id)

    asset_id = Field(Integer, ForeignKey('asset.id'))

    serial_number = Field(String)


class EquipmentFamily(Model):
    family_id = Field(String, nullable=False, unique=True)
    model = Field(String, nullable=False, unique=True)


class Event(Model, CreationDateTimeMixin):
    event_id = Field(String, nullable=False, unique=True, default=random_id)

    asset_id = Field(Integer, ForeignKey('asset.id'))

    date = Field(DateTime)

    creator_id = Field(String, nullable=False)
    creator_alias = Field(String, nullable=False)

    removed = Field(Boolean, nullable=False, default=False)
    removed_date = Field(DateTime)
    remover_id = Field(String)
    remover_alias = Field(String)

    status_id = Field(Integer, ForeignKey('event_status.id'))
    status = relationship('EventStatus', foreign_keys=status_id)


class EventStatus(Model):
    status_id = Field(String, nullable=False, unique=True)
    position = Field(Integer, nullable=False, unique=True)
    label = Field(String, nullable=False, unique=True)
