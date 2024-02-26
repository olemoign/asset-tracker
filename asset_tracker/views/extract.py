"""Asset tracker views: assets lists and read/update."""

import json
from datetime import date

from parsys_utilities import ADMIN_PRINCIPAL
from parsys_utilities.sql import windowed_query
from pyramid.security import Allow
from pyramid.view import view_config
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from asset_tracker import models

MAX_CONSUMABLES = 7
MAX_SOFTWARES = 2


class AssetsExtract:
    """Extract assets."""

    __acl__ = [
        (Allow, None, 'assets-extract', 'assets-extract'),
        (Allow, None, ADMIN_PRINCIPAL, 'assets-extract'),
    ]

    def __init__(self, request):
        self.request = request

    @staticmethod
    def get_csv_header(max_equipments_per_asset):
        """Define the column titles for the csv file.

        From unique_software and unique_equipment, we know the exact number of columns required to display each
        information without extra column.

        Args:
            max_equipments_per_asset (int): maximum number of equipment.

        Returns:
            csv header (list): columns name.
        """
        asset_columns = [
            'asset_id',
            'asset_type',
            'tenant_id',
            'tenant_name',
            'customer_name',
            'customer_id',
            'current_location',
            'calibration_frequency',
            'status_label',
            'last_event',
            'medcapture_version',
            'notes',

            'production_date',
            'delivery_date',
            'activation_date',
            'last_calibration_date',
            'next_calibration_date',
            'warranty_end_date',

            'site_name',
            'site_type',
            'site_contact',
            'site_phone',
            'site_email',
        ]

        equipment_columns = []
        for i in range(1, max_equipments_per_asset + 1):
            # Each equipment is identified by a name and a serial number.
            equipment_columns += [
                f'equipment_{i}_name',
                f'equipment_{i}_serial_number',
                *[
                    label
                    for j in range(1, MAX_CONSUMABLES + 1)
                    for label in [
                        f'equipment_{i}_consumable_{j}_name',
                        f'equipment_{i}_consumable_{j}_expiration_date',
                    ]
                ]
            ]

        return asset_columns + equipment_columns

    def get_csv_rows(self, max_equipments_per_asset):
        """Get the asset information for the csv file.

        Args:
            max_equipments_per_asset (int): maximum number of equipment.

        Returns:
            csv body (list): information on the assets.
        """
        config = self.request.registry.settings.get('asset_tracker.config', 'parsys')
        last_event = self.request.db_session.query(func.max(models.Event.created_at)) \
            .join(models.Event.status) \
            .filter(
                models.Event.asset_id == models.Asset.id,
                models.EventStatus.status_type == 'event',
            ) \
            .scalar_subquery()
        medcapture_version = self.request.db_session.query(models.Event.extra) \
            .join(models.Event.status) \
            .filter(
                models.Event.asset_id == models.Asset.id,
                models.EventStatus.status_id == 'software_update',
                models.Event.extra.ilike('%"medcapture"%'),
            ) \
            .order_by(models.Event.created_at.desc()) \
            .limit(1) \
            .scalar_subquery()
        assets = self.request.db_session.query(models.Asset, last_event, medcapture_version) \
            .options(
                joinedload(models.Asset.tenant),
                joinedload(models.Asset.site),
                joinedload(models.Asset.status),
            ) \
            .order_by(models.Asset.asset_id)

        rows = []
        for asset, last_event, medcapture_version in windowed_query(assets, models.Asset.asset_id, 100):
            # Asset information.
            row = [
                asset.asset_id,
                asset.asset_type,
                asset.tenant.tenant_id,
                asset.tenant.name,
                asset.customer_name,
                asset.customer_id,
                asset.current_location,
                asset.calibration_frequency,
                asset.status.label(config),
                last_event,
                json.loads(medcapture_version)['software_version'] if medcapture_version else None,
                asset.notes,
                asset.production,
                asset.delivery,
                asset.activation,
                asset.calibration_last,
                asset.calibration_next,
                asset.warranty_end,
            ]

            # Site information.
            if asset.site:
                row += [
                    asset.site.name,
                    asset.site.site_type,
                    asset.site.contact,
                    asset.site.phone,
                    asset.site.email,
                ]
            else:
                # Fill with None values to maintain column alignment.
                row += [None, None, None, None, None]

            # Equipments information.
            equipments = self.request.db_session.query(models.Equipment) \
                .options(
                    joinedload(models.Equipment.family),
                    joinedload(models.Equipment.consumables).joinedload(models.Consumable.family),
                ) \
                .filter(models.Equipment.asset_id == asset.id) \
                .all()

            for equipment in equipments:
                empty_consumables_count = MAX_CONSUMABLES - len(equipment.consumables)
                consumables = [(c.family.model, c.expiration_date) for c in equipment.consumables]
                row += [
                    equipment.family.model,
                    equipment.serial_number,
                    *[element for consumable in consumables for element in consumable],
                    *[None for _i in range(empty_consumables_count * 2)],
                ]

            empty_equipment_count = max_equipments_per_asset - len(equipments)
            for _ in range(empty_equipment_count):
                # Fill with None values to maintain column alignment.
                row += [None, None]
                for _ in range(MAX_CONSUMABLES):
                    row += [None, None]

            rows.append(row)

        return rows

    @view_config(route_name='assets-extract', request_method='GET', permission='assets-extract', renderer='csv')
    def extract_get(self):
        """Download Asset data. Write Asset information in csv file.

        Returns:
            (dict): header (list) and rows (list) of csv file.
        """
        # Find maximum number of equipments per asset.
        asset_with_most_equipments = self.request.db_session.query(models.Asset) \
            .join(models.Asset.equipments) \
            .group_by(models.Asset.id) \
            .order_by(func.count(models.Asset.equipments).desc()) \
            .first()

        max_equipments = len(asset_with_most_equipments.equipments) if asset_with_most_equipments else 0

        # Override attributes of response.
        filename = f'{date.today():%Y%m%d}_assets.csv'
        self.request.response.content_disposition = f'attachment;filename={filename}'

        return {
            'header': self.get_csv_header(max_equipments),
            'rows': self.get_csv_rows(max_equipments),
        }


def includeme(config):
    config.add_route(pattern='assets/extract/', name='assets-extract', factory=AssetsExtract)
