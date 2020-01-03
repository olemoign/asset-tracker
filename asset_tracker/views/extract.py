"""Asset tracker views: assets lists and read/update."""
from datetime import datetime

from parsys_utilities.authorization import Right
from pyramid.security import Allow
from pyramid.view import view_config
from sqlalchemy import desc
from sqlalchemy.orm import joinedload

from asset_tracker import models
from asset_tracker.constants import ADMIN_PRINCIPAL


class AssetsExtract(object):
    """Extract assets."""

    __acl__ = [
        (Allow, None, 'assets-extract', 'assets-extract'),
        (Allow, None, ADMIN_PRINCIPAL, 'assets-extract'),
    ]

    def __init__(self, request):
        self.request = request

    @staticmethod
    def get_csv_header(max_software_per_asset, max_equipment_per_asset):
        """Define the column titles for the csv file.

        From unique_software and unique_equipment, we know the exact number of columns required to display each
        information without extra column.

        Args:
            max_software_per_asset (int): number of distinct software.
            max_equipment_per_asset (int): number of distinct equipment.

        Returns:
            csv header (list): columns name.
        """
        asset_columns = [
            'asset_id',
            'asset_type',
            'tenant_key',
            'customer_name',
            'customer_id',
            'current_location',
            'calibration_frequency',
            'status_label',
            'notes',

            'production_date',
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

        # Each software is identified by a name and a version.
        software_columns = [
            label
            for i in range(1, max_software_per_asset + 1)
            for label in {f'software_{i}_name', f'software_{i}_version'}
        ]

        # Each equipment is identified by a name and a serial number.
        equipment_columns = [
            label
            for i in range(1, max_equipment_per_asset + 1)
            for label in {
                f'equipment_{i}_name',
                f'equipment_{i}_serial_number',
            }
        ]

        return asset_columns + software_columns + equipment_columns

    @staticmethod
    def get_csv_rows(db_session, unique_software, unique_equipment, tenants):
        """Get the asset information for the csv file.

        Args:
            db_session (sqlalchemy.orm.session.Session): current db session.
            unique_software (set): all the names of the deployed software.
            unique_equipment (tuple): all the names of the deployed equipment.
            tenants (dict): authorized tenants to extract data.

        Returns:
            csv body (list): information on the assets.
        """
        assets = db_session.query(models.Asset) \
            .options(joinedload(models.Asset.site), joinedload(models.Asset.status)) \
            .filter(models.Asset.tenant_id.in_(tenants.keys())) \
            .order_by(models.Asset.asset_id)

        rows = []
        for asset in assets:
            # Asset information.
            row = [
                asset.asset_id,
                asset.asset_type,
                tenants[asset.tenant_id],
                asset.customer_name,
                asset.customer_id,
                asset.current_location,
                asset.calibration_frequency,
                asset.status.label,
                asset.notes,
                asset.production,
                asset.activation_first,
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

            # Software information.
            software_updates = db_session.query(models.Event) \
                .join(models.EventStatus) \
                .filter(
                    models.Event.asset_id == asset.id,
                    models.EventStatus.status_id == 'software_update',
                ).order_by(desc('date'))

            # Get last version of each software.
            most_recent_soft_per_asset = {}
            for update in software_updates:
                extra_json = update.extra_json
                software_name, software_version = extra_json['software_name'], extra_json['software_version']
                if software_name not in most_recent_soft_per_asset:
                    most_recent_soft_per_asset[software_name] = software_version

            # Format software output.
            for software_name in unique_software:
                if software_name in most_recent_soft_per_asset:
                    row += [software_name, most_recent_soft_per_asset[software_name]]
                else:
                    # Fill with None values to maintain column alignment.
                    row += [None, None]

            # Equipment information.
            asset_equipment = db_session.query(
                    models.EquipmentFamily.model,
                    models.Equipment.serial_number,
                ) \
                .join(models.Equipment) \
                .filter(models.Equipment.asset_id == asset.id).all()

            for equipment_name in unique_equipment:
                equipment = next((e for e in asset_equipment if e[0] == equipment_name), None)
                if equipment:
                    row += [*equipment]
                else:
                    # Fill with None values to maintain column alignment.
                    row += [None, None, None, None]

            rows.append(row)

        return rows

    def get_extract_tenants(self):
        """Get for which tenants the current user can extract assets information."""
        # Admins have access to all tenants.
        if self.request.user.is_admin:
            return {tenant['id']: tenant['name'] for tenant in self.request.user.tenants}

        else:
            return {
                tenant['id']: tenant['name']
                for tenant in self.request.user.tenants
                if Right(name='assets-extract', tenant=tenant['id']) in self.request.effective_principals
            }

    @view_config(route_name='assets-extract', request_method='GET', permission='assets-extract', renderer='csv')
    def extract_get(self):
        """Download Asset data. Write Asset information in csv file.

        Returns:
            (dict): header (list) and rows (list) of csv file
        """
        # Authorized tenants.
        tenants = self.get_extract_tenants()

        # Dynamic data - software.
        # Find unique software name.
        software_updates = self.request.db_session.query(models.Event) \
            .join(models.Asset, models.Event.asset_id == models.Asset.id) \
            .filter(models.Asset.tenant_id.in_(tenants.keys())) \
            .join(models.EventStatus, models.Event.status_id == models.EventStatus.id) \
            .filter(models.EventStatus.status_id == 'software_update')

        unique_software = set(update.extra_json['software_name'] for update in software_updates)

        # Dynamic data - equipment.
        # Find the name of the deployed equipment.
        equipment_names = self.request.db_session.query(models.Equipment.family_id, models.EquipmentFamily.model) \
            .join(models.EquipmentFamily, models.Equipment.family_id == models.EquipmentFamily.id) \
            .join(models.Asset, models.Equipment.asset_id == models.Asset.id) \
            .filter(models.Asset.tenant_id.in_(tenants.keys())) \
            .group_by(models.Equipment.family_id, models.EquipmentFamily.model) \
            .order_by(models.EquipmentFamily.model)

        # Get EquipmentFamily.model.
        unique_equipment = tuple(e[1] for e in equipment_names)

        # Override attributes of response.
        filename = f'{datetime.utcnow():%Y%m%d}_assets.csv'
        self.request.response.content_disposition = f'attachment;filename={filename}'

        return {
            'header': self.get_csv_header(len(unique_software), len(unique_equipment)),
            'rows': self.get_csv_rows(self.request.db_session, unique_software, unique_equipment, tenants),
        }


def includeme(config):
    config.add_route(pattern='assets/extract/', name='assets-extract', factory=AssetsExtract)
