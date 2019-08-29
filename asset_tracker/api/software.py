"""Asset Tracker software management."""
import os
import re
from collections import OrderedDict
from datetime import datetime
from json import dumps, loads, JSONDecodeError

from depot.manager import DepotManager
from pyramid.httpexceptions import HTTPBadRequest, HTTPInternalServerError, HTTPNotFound, HTTPOk
from pyramid.security import Allow
from pyramid.view import view_config
from sentry_sdk import capture_exception
from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound

from asset_tracker import models
from asset_tracker.constants import ADMIN_PRINCIPAL


def get_archi_from_file(file_name):
    """Get architecture (32 or 64 bits) version from file name.

    Args:
        file_name (str): file name.

    Returns:
        int: software architecture, 32 or 64.

    """
    # Remove file extension.
    file_name = os.path.splitext(file_name)[0]
    product_name = file_name.split('-')[0]
    # noinspection PyTypeChecker
    return 32 if product_name.endswith('32') else 64


def get_version_from_file(file_name):
    """Get software version from file name.

    Args:
        file_name (str): file name.

    Returns:
        str: software version.

    """
    # Remove file extension.
    file_name = os.path.splitext(file_name)[0]
    return re.search(r'[0-9]+\.[0-9]+\.[0-9]+.*', file_name).group()


def sort_versions(version):
    """Sort versions according to natural order.

    When comparing strings, 'beta9' > 'beta15' because '9' > '1'. Actually, for humans, it should be '15' > '9'.
    Here, we split the incoming string between text and digits and convert digits to int so that Python will be able
    to compare int(15) and int(9).

    Special case for final versions: 2.9.0 has only three items, less than 2.9.0-rc10. Thus we force final versions to
    the end of the list.

    Args:
        version (str): version to be sorted.

    Returns
        list: split string, with text as str and numbers as int.

    """
    # 'if text' allows us to remove the empty strings always occuring for the first and last element of the re.split().
    sort_key = []

    for substring in re.split('([0-9]+)', version):
        if substring.isdigit():
            sort_key.append(int(substring))
        elif substring and substring != '.':
            sort_key.append(substring.lower().replace('-', ''))

    # Final version.
    if len(sort_key) == 3:
        sort_key.append('zzz')

    return sort_key


class Software(object):
    """Software update WebServices: tell the assets what is the latest version and url of a given product + store what
    softwares versions a given asset is using.

    """
    __acl__ = [
        (Allow, None, 'api-software-update', 'api-software-update'),
        (Allow, None, ADMIN_PRINCIPAL, 'api-software-update'),
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
            raise HTTPBadRequest(json={'error': 'Missing product.'})
        else:
            self.product = product.lower()

        # The station can indicate what version of the software it is using.
        current = self.request.GET.get('current')

        # Release channel (alpha, beta, dev, stable).
        channel = self.request.GET.get('channel', 'stable')

        # 32 or 64 bits?
        archi_32_bits = self.request.user_agent and 'Windows NT 6.3' in self.request.user_agent

        # If storage folder wasn't set up, can't return link.
        storage = self.request.registry.settings.get('asset_tracker.software_storage')
        if not storage:
            return {}

        # Products are stored in sub-folders in the storage path.
        # As os.walk is recursive, we need to work the results a bit.
        products = next(os.walk(storage), [])
        products = products[1] if products else []
        if self.product not in products:
            raise HTTPNotFound(json={'error': 'Unknown product.'})

        product_folder = os.path.join(storage, self.product)
        product_files = next(os.walk(product_folder))[2]

        product_versions = {}
        for product_file in product_files:
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
                product_versions[version] = product_file

        if not product_versions:
            return {}

        # noinspection PyTypeChecker
        # Sort dictionary by version (which are the keys of the dict).
        product_versions = OrderedDict(sorted(product_versions.items(), key=lambda k: sort_versions(k[0])))

        version = self.request.GET.get('version')
        if version and version in product_versions.keys():
            file = product_versions[version]
            download_url = self.request.route_url('api-software-download', product=self.product, file=file)
            return {'version': version, 'url': download_url}

        elif version:
            return {}

        # We return only the latest version.
        product_latest = product_versions.popitem(last=True)

        # Make sure we aren't in the special case where the station is using a version that hasn't been uploaded yet.
        try:
            if current and sort_versions(current) > sort_versions(product_latest[0]):
                return {}
        except TypeError:
            # In case the current version wasn't in an expected format, discard it.
            pass

        download_url = self.request.route_url('api-software-download', product=self.product, file=product_latest[1])
        return OrderedDict(version=product_latest[0], url=download_url)

    def create_config_update_event(self, config, asset):
        """Create event if configuration file changed"""
        try:
            config_status = self.request.db_session.query(models.EventStatus) \
                .filter(models.EventStatus.status_id == 'config_update').one()
        except (MultipleResultsFound, NoResultFound) as error:
            capture_exception(error)
            self.request.logger_technical.info('Missing status: config update.')
            raise HTTPInternalServerError(json={'error': 'Internal server error.'})

        last_event = asset.history(order='desc') \
            .join(models.EventStatus).filter(models.EventStatus.status_id == 'config_update').first()

        depot = DepotManager.get()

        if last_event:
            try:
                config_file = depot.get(last_event.extra_json['config'])
            except (IOError, ValueError):
                pass

            last_config = loads(config_file.read().decode('utf-8'))

        if not last_event or (last_config and last_config != config):
            file_id = depot.create(bytes(dumps(config), 'utf-8'), 'file', 'application/json')

            new_event = models.Event(
                status=config_status,
                date=datetime.utcnow().date(),
                creator_id=self.request.user.id,
                creator_alias=self.request.user.alias,
                extra=dumps({'config': file_id}),
            )

            # noinspection PyProtectedMember
            asset._history.append(new_event)
            self.request.db_session.add(new_event)

    def create_version_update_event(self, software_version, asset):
        """Create event if software version was updated"""
        latest_events = asset.history(order='desc') \
            .join(models.EventStatus).filter(models.EventStatus.status_id == 'software_update')

        last_event_generator = (e for e in latest_events if e.extra_json['software_name'] == self.product)
        last_event = next(last_event_generator, None)

        if not last_event or last_event.extra_json['software_version'] != software_version:
            try:
                software_status = self.request.db_session.query(models.EventStatus) \
                    .filter(models.EventStatus.status_id == 'software_update').one()
            except (MultipleResultsFound, NoResultFound) as error:
                capture_exception(error)
                self.request.logger_technical.info('Missing status: software update.')
                raise HTTPInternalServerError(json={'error': 'Internal server error.'})

            new_event = models.Event(
                status=software_status,
                date=datetime.utcnow().date(),
                creator_id=self.request.user.id,
                creator_alias=self.request.user.alias,
                extra=dumps({'software_name': self.product, 'software_version': software_version}),
            )

            # noinspection PyProtectedMember
            asset._history.append(new_event)
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
            raise HTTPBadRequest(json={'error': 'Missing product.'})
        else:
            self.product = self.request.GET['product'].lower()

        # Make sure the JSON provided is valid.
        try:
            json = self.request.json
        except JSONDecodeError as error:
            capture_exception(error)
            raise HTTPBadRequest(json={'error': 'Invalid JSON.'})

        # Check if asset exists (cart, station, telecardia).
        try:
            station_login = self.request.user.login
        except KeyError:
            raise HTTPBadRequest(json={'error': 'Invalid authentication.'})

        asset = self.request.db_session.query(models.Asset).filter_by(asset_id=station_login).first()
        if not asset:
            raise HTTPNotFound(json={'error': 'Unknown asset.'})

        software_version = json.get('version')
        config = json.get('config')
        if not config and not software_version:
            raise HTTPBadRequest(json='Missing configuration data.')

        # Handle software version update.
        self.create_version_update_event(software_version, asset)

        # Handle software configuration file update.
        self.create_config_update_event(config, asset)

        return HTTPOk(json='Information received.')


def includeme(config):
    config.add_route(pattern='download/{product}/{file}', name='api-software-download')
    config.add_route(pattern='update/', name='api-software-update', factory=Software)
