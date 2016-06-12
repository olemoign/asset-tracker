from collections import OrderedDict
from operator import attrgetter
from pyramid.i18n import TranslationString as _

from .utilities.domain_model import CreationDateTimeMixin, Date, DateTime, Enum, hybrid_property, Integer, Field, \
    ForeignKey, Model, relationship, select, String


class Asset(Model, CreationDateTimeMixin):
    tenant_id = Field(String)
    asset_id = Field(String)

    customer_id = Field(String)
    customer_name = Field(String)

    site = Field(String)
    current_location = Field(String)
    notes = Field(String)

    history = relationship('Event', lazy='dynamic')
    equipments = relationship('Equipment', lazy='dynamic')

    next_calibration = Field(Date)

    @hybrid_property
    def status(self):
        if self.history:
            return sorted(self.history, key=attrgetter('date'), reverse=True)[0].status
        else:
            return None

    @status.expression
    def status(cls):
        return select([Event.status]).where(Event.asset_id == cls.id).order_by(Event.date.desc()).limit(1)


class EquipmentFamily(Model):
    model = Field(String)


class Equipment(Model):
    family_id = Field(Integer, ForeignKey('equipment_family.id'))
    family = relationship('EquipmentFamily', foreign_keys=family_id)

    asset_id = Field(Integer, ForeignKey('asset.id'))

    serial_number = Field(String)


class Event(Model):
    asset_id = Field(Integer, ForeignKey('asset.id'))

    date = Field(DateTime)

    creator_id = Field(Integer)
    creator_alias = Field(String)

    status = Field(Enum('service', 'repair', 'calibration', 'transit_parsys', 'transit_customer', name='status'))

    status_labels = OrderedDict([
        ('service', _('In service')),
        ('repair', _('In repair')),
        ('calibration', _('In calibration')),
        ('transit_parsys', _('In transit to Parsys')),
        ('transit_customer', _('In transit to customer')),
    ])
