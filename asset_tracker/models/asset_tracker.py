from operator import attrgetter

from dateutil.relativedelta import relativedelta
from parsys_utilities.model import and_, CreationDateTimeMixin, DateTime, Field, ForeignKey, hybrid_property, \
    Integer, join, Model, relationship, select, String

from asset_tracker.constants import CALIBRATION_FREQUENCY_YEARS


class Asset(Model, CreationDateTimeMixin):
    tenant_id = Field(String, nullable=False)
    asset_id = Field(String, nullable=False)

    customer_id = Field(String)
    customer_name = Field(String)

    site = Field(String)
    current_location = Field(String)
    notes = Field(String)

    software_version = Field(String)
    history = relationship('Event', lazy='dynamic')
    equipments = relationship('Equipment', lazy='dynamic')

    @hybrid_property
    def status(self):
        if self.history:
            return sorted(self.history, key=attrgetter('date', 'created_at'), reverse=True)[0].status

    # noinspection PyMethodParameters
    @status.expression
    def status(cls):
        return select([EventStatus]).select_from(join(Event, EventStatus)).where(Event.asset_id == cls.id) \
            .order_by(Event.date.desc(), Event.created_at.desc()).limit(1)

    @hybrid_property
    def calibration_next(self):
        if self.history:
            calibration_last = self.history.join(EventStatus).filter(EventStatus.status_id == 'calibration') \
                .order_by(Event.date.desc()).first()
            if calibration_last:
                return calibration_last.date.date() + relativedelta(years=CALIBRATION_FREQUENCY_YEARS)

    # noinspection PyMethodParameters
    @calibration_next.expression
    def calibration_next(cls):
        # TODO: this returns the last calibration, which works as this function is used for ordering and
        # currently the delta between next and last calibration is the same for all assets.
        # This will need work if the delta is no longer the same for all.
        return select([Event.date]).select_from(join(Event, EventStatus)). \
            where(and_(Event.asset_id == cls.id, EventStatus.status_id == 'calibration')) \
            .order_by(Event.date.desc()).limit(1)


class Equipment(Model):
    family_id = Field(Integer, ForeignKey('equipment_family.id'))
    family = relationship('EquipmentFamily', foreign_keys=family_id)

    asset_id = Field(Integer, ForeignKey('asset.id'))

    serial_number = Field(String)


class EquipmentFamily(Model):
    family_id = Field(String)
    model = Field(String)


class Event(Model, CreationDateTimeMixin):
    asset_id = Field(Integer, ForeignKey('asset.id'))

    date = Field(DateTime)

    creator_id = Field(String)
    creator_alias = Field(String)

    status_id = Field(Integer, ForeignKey('event_status.id'))
    status = relationship('EventStatus', foreign_keys=status_id)


class EventStatus(Model):
    status_id = Field(String)
    position = Field(Integer)
    label = Field(String)
