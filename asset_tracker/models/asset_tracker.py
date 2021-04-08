from json import loads

from dateutil.relativedelta import relativedelta
from parsys_utilities.model import CreationDateTimeMixin, Model
from parsys_utilities.random import random_id
from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, Table, Unicode as String, UniqueConstraint
from sqlalchemy.ext.hybrid import hybrid_method, hybrid_property
from sqlalchemy.orm import backref, relationship

from asset_tracker.constants import WARRANTY_DURATION_YEARS


class Asset(Model, CreationDateTimeMixin):
    asset_id = Column(String, nullable=False, unique=True)
    tenant_id = Column(String, nullable=False)
    user_id = Column(String)  # Received from RTA during station creation/update.

    tenant_info_id = Column(Integer, ForeignKey('tenant_info.id'), nullable=False)
    tenant_info = relationship('TenantInfo', foreign_keys=tenant_info_id, backref='assets', uselist=False)

    @property
    def is_linked(self):
        """Asset is_linked if it received user_id from RTA.

        Returns:
            bool.
        """
        return bool(self.user_id)

    asset_type = Column(String, nullable=False)
    hardware_version = Column(String)
    mac_wifi = Column(String)
    mac_ethernet = Column(String)

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

        Returns:
            sqlalchemy.orm.query.Query.
        """
        if order == 'asc':
            history = self._history.filter_by(removed=False).order_by(Event.date, Event.created_at)
        else:
            history = self._history.filter_by(removed=False).order_by(Event.date.desc(), Event.created_at.desc())

        if filter_config:
            history = history.join(Event.status).filter(EventStatus.status_type != 'config')

        return history

    status_id = Column(Integer, ForeignKey('event_status.id'), nullable=False)
    status = relationship('EventStatus', foreign_keys=status_id, uselist=False)

    calibration_frequency = Column(Integer)
    calibration_next = Column(Date)

    def _get_asset_dates(self):
        """Compute all the dates in one method to avoid too many sql request."""
        self._asset_dates = {}
        asset_query = self.history('asc').join(Event.status)

        production = asset_query.filter(EventStatus.status_id == 'stock_parsys').first()
        self._asset_dates['production'] = production.date if production else None

        delivery = asset_query.filter(EventStatus.status_id == 'on_site').first()
        self._asset_dates['delivery'] = delivery.date if delivery else None
        self._asset_dates['warranty_end'] = delivery.date + relativedelta(years=WARRANTY_DURATION_YEARS) \
            if delivery else None

        activation = asset_query.filter(EventStatus.status_id == 'service').first()
        self._asset_dates['activation'] = activation.date if activation else None

        calibration_last = asset_query.filter(EventStatus.status_id == 'calibration').first()
        if production and calibration_last:
            self._asset_dates['calibration_last'] = max(production.date, calibration_last.date)
        for status in ['calibration_last', 'production', 'delivery', 'activation']:
            if locals().get(status):
                self._asset_dates['calibration_last'] = locals()[status].date
                break
        else:
            self._asset_dates['calibration_last'] = None

    @property
    def asset_dates(self):
        if not hasattr(self, '_asset_dates'):
            self._get_asset_dates()

        return self._asset_dates

    @property
    def activation(self):
        """Get the date of the asset first activation.

        Returns:
            datetime.datetime.
        """
        return self.asset_dates['activation']

    @property
    def calibration_last(self):
        """Get the date of the asset last calibration.

        Returns:
            datetime.datetime.
        """
        return self.asset_dates['calibration_last']

    @property
    def delivery(self):
        """Get the date of the asset first activation.

        Returns:
            datetime.datetime.
        """
        return self.asset_dates['delivery']

    @property
    def production(self):
        """Get the date of the asset production.

        Returns:
            datetime.datetime.
        """
        return self.asset_dates['production']

    @property
    def warranty_end(self):
        """Get the date of the end of the asset warranty.

        Returns:
            datetime.datetime.
        """
        return self.asset_dates['warranty_end']


class Consumable(Model):
    family_id = Column(Integer, ForeignKey('consumable_family.id'), nullable=False)
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
    family_id = Column(Integer, ForeignKey('equipment_family.id'), nullable=False)
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
        """Return dictionary from extra.

        Returns:
            dict.
        """
        try:
            return loads(self.extra)
        except TypeError:
            return {}


class EventStatus(Model):
    status_id = Column(String, nullable=False, unique=True)

    position = Column(Integer, nullable=False, unique=True)
    status_type = Column(String, nullable=False)
    _label = Column(String, nullable=False, unique=True)
    _label_marlink = Column(String, unique=True)

    @hybrid_method
    def label(self, config):
        """Get an asset status label based on config.

        Args:
            config (str).

        Returns:
            str.
        """
        return self._label_marlink if config == 'marlink' and self._label_marlink else self._label


class Site(Model, CreationDateTimeMixin):
    site_id = Column(String, default=random_id, nullable=False, unique=True)
    tenant_id = Column(String, nullable=False)

    tenant_info_id = Column(Integer, ForeignKey('tenant_info.id'), nullable=False)
    tenant_info = relationship('TenantInfo', foreign_keys=tenant_info_id, backref='sites', uselist=False)

    name = Column(String, nullable=False, unique=True)
    site_type = Column(String)

    contact = Column(String)
    phone = Column(String)
    email = Column(String)


class TenantInfo(Model):
    tenant_id = Column(String, nullable=False, unique=True)
    name = Column(String, nullable=False)
