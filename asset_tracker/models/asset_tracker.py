from json import loads

from dateutil.relativedelta import relativedelta
from parsys_utilities import random_id
from parsys_utilities.sql.model import CreationDateTimeMixin, Model, TZDateTime
from sqlalchemy import Boolean, Column, Date, ForeignKey, Integer, Table, Unicode as String, UniqueConstraint, asc, \
    desc, select
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

from asset_tracker.constants import WARRANTY_DURATION_YEARS


class Asset(Model, CreationDateTimeMixin):
    asset_id = Column(String, nullable=False, unique=True)
    tenant_id = Column(Integer, ForeignKey('tenant.id'), nullable=False)
    tenant = relationship('Tenant', foreign_keys=tenant_id, uselist=False, back_populates='assets')
    user_id = Column(String)  # Received from RTA during station creation/update.

    @hybrid_property
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
    site = relationship('Site', foreign_keys=site_id, uselist=False, back_populates='assets')

    current_location = Column(String)
    notes = Column(String)

    calibration_frequency = Column(Integer)
    calibration_next = Column(Date)

    status_id = Column(Integer, ForeignKey('event_status.id'), nullable=False)
    status = relationship('EventStatus', foreign_keys=status_id, uselist=False)

    equipments = relationship('Equipment', back_populates='asset')

    _history = relationship('Event', lazy='dynamic', back_populates='asset')

    def add_event(self, event):
        """Add event to asset history.

        Args:
            asset_tracker.models.Event.
        """
        self._history.append(event)
        self.status = self.history('desc', filter_config=True).first().status

    def history(self, order, filter_config=False):
        """Filter removed events from history.

        Args:
            order (str): asc/desc.
            filter_config (bool): should we get config updates?

        Returns:
            sqlalchemy.orm.query.Query.
        """
        order_func = asc if order == 'asc' else desc
        events = self._history.filter(~Event.removed).order_by(order_func(Event.date), order_func(Event.created_at))

        if filter_config:
            events = events.join(Event.status).filter(EventStatus.status_type != 'config')

        return events

    @hybrid_property
    def is_decommissioned(self):
        """Asset is decommissioned.

        Returns:
            bool.
        """
        return self.status.status_id == 'decommissioned'

    # noinspection PyMethodParameters
    @is_decommissioned.expression
    def is_decommissioned(cls):
        return select(EventStatus.status_id == 'decommissioned') \
            .where(EventStatus.id == cls.status_id) \
            .scalar_subquery()

    def _get_asset_dates(self):
        """Compute all the dates in one method to avoid too many sql request."""
        self._asset_dates = {}
        asset_history = self.history('asc').join(Event.status)
        asset_history_desc = self.history('desc').join(Event.status)

        production = asset_history.filter(EventStatus.status_id == 'stock_parsys').first()
        self._asset_dates['production'] = production.date if production else None

        delivery = asset_history.filter(EventStatus.status_id == 'transit_customer').first()
        self._asset_dates['delivery'] = delivery.date if delivery else None

        activation = asset_history.filter(EventStatus.status_id == 'service').first()
        self._asset_dates['activation'] = activation.date if activation else None
        self._asset_dates['warranty_end'] = (
            activation.date + relativedelta(years=WARRANTY_DURATION_YEARS)
            if not self.is_decommissioned and activation
            else None
        )

        if self.asset_type == 'consumables_case':
            self._asset_dates['calibration_last'] = None
        else:
            calibration_last = asset_history_desc.filter(EventStatus.status_id == 'calibration').first()
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

    @hybrid_property
    def activation(self):
        """Get the date of the asset first activation.

        Returns:
            datetime.date.
        """
        return self.asset_dates['activation']

    @hybrid_property
    def calibration_last(self):
        """Get the date of the asset last calibration.

        Returns:
            datetime.date.
        """
        return self.asset_dates['calibration_last']

    @hybrid_property
    def delivery(self):
        """Get the date of the asset first activation.

        Returns:
            datetime.date.
        """
        return self.asset_dates['delivery']

    @hybrid_property
    def production(self):
        """Get the date of the asset production.

        Returns:
            datetime.date.
        """
        return self.asset_dates['production']

    @hybrid_property
    def warranty_end(self):
        """Get the date of the end of the asset warranty.

        Returns:
            datetime.date.
        """
        return self.asset_dates['warranty_end']


class Consumable(Model):
    family_id = Column(Integer, ForeignKey('consumable_family.id'), nullable=False)
    family = relationship('ConsumableFamily', foreign_keys=family_id, uselist=False)

    equipment_id = Column(Integer, ForeignKey('equipment.id'), nullable=False)
    equipment = relationship('Equipment', foreign_keys=equipment_id, uselist=False, back_populates='consumables')

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
        'EquipmentFamily', secondary=consumable_families_equipment_families, back_populates='consumable_families'
    )


class Equipment(Model):
    family_id = Column(Integer, ForeignKey('equipment_family.id'), nullable=False)
    family = relationship('EquipmentFamily', foreign_keys=family_id, uselist=False, back_populates='equipments')

    asset_id = Column(Integer, ForeignKey('asset.id'), nullable=False)
    asset = relationship('Asset', foreign_keys=asset_id, uselist=False, back_populates='equipments')

    serial_number = Column(String)

    consumables = relationship('Consumable', back_populates='equipment')


class EquipmentFamily(Model):
    family_id = Column(String, nullable=False, unique=True)
    model = Column(String, nullable=False, unique=True)

    equipments = relationship('Equipment', back_populates='family')
    consumable_families = relationship(
        'ConsumableFamily', secondary=consumable_families_equipment_families, back_populates='equipment_families'
    )


class Event(Model, CreationDateTimeMixin):
    event_id = Column(String, default=random_id, nullable=False, unique=True)

    asset_id = Column(Integer, ForeignKey('asset.id'), nullable=False)
    asset = relationship('Asset', foreign_keys=asset_id, uselist=False, back_populates='_history')

    date = Column(Date, nullable=False)

    creator_id = Column(String, nullable=False)
    creator_alias = Column(String, nullable=False)

    removed = Column(Boolean, nullable=False, default=False)
    removed_at = Column(TZDateTime)
    remover_id = Column(String)
    remover_alias = Column(String)

    status_id = Column(Integer, ForeignKey('event_status.id'), nullable=False)
    status = relationship('EventStatus', foreign_keys=status_id, uselist=False)

    extra = Column(String)

    @property
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
    tenant_id = Column(Integer, ForeignKey('tenant.id'), nullable=False)
    tenant = relationship('Tenant', foreign_keys=tenant_id, uselist=False, back_populates='sites')

    name = Column(String, nullable=False, unique=True)
    site_type = Column(String)

    contact = Column(String)
    phone = Column(String)
    email = Column(String)

    assets = relationship('Asset', back_populates='site')


class Tenant(Model):
    tenant_id = Column(String, nullable=False, unique=True)
    name = Column(String, nullable=False)

    assets = relationship('Asset', back_populates='tenant')
    sites = relationship('Site', back_populates='tenant')
