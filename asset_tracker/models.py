from collections import OrderedDict
from pyramid.i18n import TranslationString as _

from .utilities.domain_model import CreationDateTimeMixin, Date, Enum, Integer, Field, ForeignKey, Model, relationship, String


class Asset(Model, CreationDateTimeMixin):
    asset_id = Field(String)
    customer = Field(String)
    site = Field(String)
    notes = Field(String)
    history = relationship('Event', order_by='Event.date')
    current_location = Field(String)
    equipments = relationship('Equipment')


class EquipmentFamily(Model):
    model = Field(String)


class Equipment(Model):
    family_id = Field(Integer, ForeignKey('equipment_family.id'))
    family = relationship('EquipmentFamily', foreign_keys=family_id)
    asset_id = Field(Integer, ForeignKey('asset.id'))
    serial_number = Field(String)


class Event(Model):
    asset_id = Field(Integer, ForeignKey('asset.id'))
    date = Field(Date)
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
