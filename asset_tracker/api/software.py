"""Asset Tracker software management."""
import json
import re
from datetime import date, datetime
from pathlib import Path

import packaging.version
from depot.manager import DepotManager
from pyramid.httpexceptions import HTTPBadRequest, HTTPNotFound, HTTPOk
from pyramid.security import Allow
from pyramid.view import view_config
from sentry_sdk import capture_exception, capture_message

from asset_tracker import models


def get_archi_from_file(file_name):
    """Get architecture (32 or 64 bits) version from file name.

    Args:
        file_name (pathlib.Path): file name.

    Returns:
        int: software architecture, 32 or 64.
    """
    # Remove file extension.
    product_name = file_name.stem.split('-')[0]
    return 32 if product_name.endswith('32') else 64


def get_product_files(product_folder):
    """Get the list of product files. Mocking pathlib.Path was too difficult, this (very simple) function was created
    for testing purposes.

    Args:
        product_folder (pathlib.Path).

    Returns:
        list.
    """
    return [item for item in product_folder.iterdir() if item.is_file()]


def get_version_from_file(file_name):
    """Get software version from file name.

    Args:
        file_name (pathlib.Path): file name.

    Returns:
        str: software version.
    """
    # Remove file extension.
    return re.search(r'\d+\.\d+\.\d+.*', file_name.stem).group()


class Software:
    """Software update WebServices: tell the assets what is the latest version and url of a given product + store what
    software versions a given asset is using.
    """

    __acl__ = [
        (Allow, None, 'api-software-update', 'api-software-update'),
    ]

    def __init__(self, request):
        self.request = request
        self.product = None

    @view_config(route_name='api-software-update', request_method='GET', permission='api-software-update',
                 renderer='json')
    def software_update_get(self):
        """Return what is the lastest version of a product in a given branch (alpha/beta/dev/stable) and the url
        where to download the package.

        Query string:
            product (mandatory).
            channel (optional): product channel (in 'alpha', 'beta', 'dev', 'stable').
            version (optional): if we want the url of one specific version.
        """
        product = self.request.GET.get('product')
        if not product:
            capture_message('Missing product.')
            raise HTTPBadRequest(json={'error': 'Missing product.'})
        else:
            self.product = product.lower()

        # The station can indicate what version of the software it is using.
        current = self.request.GET.get('current')
        if current:
            try:
                current = packaging.version.Version(current)
            except packaging.version.InvalidVersion as error:
                capture_exception(error)
                # The current version wasn't in an expected format.
                raise HTTPBadRequest(json={'error': 'Invalid current version.'})

        # Release channel (alpha, beta, dev, stable).
        channel = self.request.GET.get('channel', 'stable')
        # 32 or 64 bits?
        archi_32_bits = bool(self.request.user_agent and 'Windows NT 6.3' in self.request.user_agent)

        # If storage folder wasn't set up, can't return link.
        storage_path = self.request.registry.settings.get('asset_tracker.software_storage')
        if not storage_path:
            return {'updateAvailable': False} if current else {}

        # Products are stored in sub-folders in the storage path.
        product_folder = Path(storage_path) / self.product
        if not product_folder.is_dir():
            return {'updateAvailable': False} if current else {}

        product_versions = {}
        for product_file in get_product_files(product_folder):
            # Test channel.
            version = get_version_from_file(product_file)
            alpha = 'alpha' in version and channel in ['alpha', 'dev']
            beta = 'beta' in version and channel in ['alpha', 'beta', 'dev']
            stable = 'alpha' not in version and 'beta' not in version
            wanted_channel = alpha or beta or stable

            # Test_archi.
            archi = get_archi_from_file(product_file)
            wanted_archi = archi_32_bits == (archi == 32)

            if wanted_channel and wanted_archi:
                # Handle formats like 4.1.0-alpha5-26-g014084c7e in at.dev for compatibility with packaging.version.
                parsed_intermediate_version = re.search(r'\d+\.\d+\.\d+-\w+-\d+(-{1}.*)', version)
                if parsed_intermediate_version:
                    version = version.replace(parsed_intermediate_version.group(1), '')

                product_versions[version] = product_file.name

        if not product_versions:
            return {'updateAvailable': False} if current else {}

        # Sort dictionary by version (which are the keys of the dict).
        # noinspection PyTypeChecker
        product_versions = dict(sorted(product_versions.items(), key=lambda k: packaging.version.Version(k[0])))

        version = self.request.GET.get('version')
        if version and version in product_versions:
            file = product_versions[version]
            download_url = self.request.route_url('api-software-download', product=self.product, file=file)
            return {'version': version, 'url': download_url}

        elif version:
            return {}

        # We return only the latest version.
        product_latest = product_versions.popitem()
        # Make sure we aren't in the special case where the station is using a version that hasn't been uploaded yet.
        if current and current > packaging.version.Version(product_latest[0]):
            return {'updateAvailable': False}

        download_url = self.request.route_url('api-software-download', product=self.product, file=product_latest[1])
        if current:
            return {'updateAvailable': True, 'version': product_latest[0], 'url': download_url}
        else:
            return {'version': product_latest[0], 'url': download_url}

    def create_config_update_event(self, config, asset):
        """Create event if configuration file changed.

        Args:
            config (dict):
            asset (asset_tracker.models.Asset).
        """
        depot = DepotManager.get()
        last_config = None

        last_event = asset.history(order='desc') \
            .join(models.Event.status) \
            .filter(models.EventStatus.status_id == 'config_update') \
            .first()
        if last_event:
            try:
                config_file = depot.get(last_event.extra_json['config'])
                last_config = json.loads(config_file.read().decode('utf-8'))
            except (json.JSONDecodeError, OSError, TypeError, ValueError) as error:
                capture_exception(error)

        if not last_event or last_config != config:
            file_id = depot.create(bytes(json.dumps(config), 'utf-8'), 'config.json', 'application/json')
            # noinspection PyArgumentList
            new_event = models.Event(
                creator_id=self.request.user.id,
                creator_alias=self.request.user.alias,
                date=date.today(),
                extra=json.dumps({'config': file_id}),
                status=self.request.db_session.query(models.EventStatus).filter_by(status_id='config_update').one(),
            )
            asset.add_event(new_event)
            self.request.db_session.add(new_event)

    def create_version_update_event(self, software_version, asset):
        """Create event if software version was updated.

        Args:
            software_version (str).
            asset (asset_tracker.models.Asset).
        """
        latest_events = asset.history(order='desc') \
            .join(models.Event.status) \
            .filter(models.EventStatus.status_id == 'software_update')
        last_event_generator = (e for e in latest_events if e.extra_json['software_name'] == self.product)
        last_event = next(last_event_generator, None)

        if not last_event or last_event.extra_json['software_version'] != software_version:
            # noinspection PyArgumentList
            new_event = models.Event(
                creator_id=self.request.user.id,
                creator_alias=self.request.user.alias,
                date=datetime.utcnow().date(),
                extra=json.dumps({'software_name': self.product, 'software_version': software_version}),
                status=self.request.db_session.query(models.EventStatus).filter_by(status_id='software_update').one(),
            )
            asset.add_event(new_event)
            self.request.db_session.add(new_event)

    @view_config(route_name='api-software-update', request_method='POST', permission='api-software-update',
                 require_csrf=False, renderer='json')
    def software_update_post(self):
        """Receive software(s) version and/or software(s) configuration file.

        Query string:
            product (mandatory).

        Body (json, it is mandatory to provide at least one of the following):
            version.
            config.
        """
        # Get product name (medcapture, camagent).
        if not self.request.GET.get('product'):
            capture_message('Missing product.')
            raise HTTPBadRequest(json={'error': 'Missing product.'})
        else:
            self.product = self.request.GET['product'].lower()

        # Make sure the JSON provided is valid.
        try:
            post_json = self.request.json
        except json.JSONDecodeError as error:
            capture_exception(error)
            raise HTTPBadRequest(json={'error': 'Invalid JSON.'})

        asset = self.request.db_session.query(models.Asset).filter_by(asset_id=self.request.user.login).first()
        if not asset:
            capture_message(f'Unknown asset: {self.request.user.login}.')
            raise HTTPNotFound(json={'error': 'Unknown asset.'})

        software_version = post_json.get('version')
        config = post_json.get('config')
        if not config and not software_version:
            capture_message('No data received.')
            raise HTTPBadRequest(json='No data received.')

        # Handle software version update.
        if software_version:
            self.create_version_update_event(software_version, asset)

        # Handle software configuration file update.
        if config:
            self.create_config_update_event(config, asset)

        return HTTPOk(json='Information received.')


def includeme(config):
    config.add_route(pattern='download/{product}/{file}', name='api-software-download')
    config.add_route(pattern='update/', name='api-software-update', factory=Software)
