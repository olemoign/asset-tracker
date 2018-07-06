import arrow
import itertools
import transaction
from celery.utils.log import get_task_logger
from sqlalchemy import create_engine

from asset_tracker import models
from parsys_utilities.celery_app import app
from parsys_utilities.sentry import sentry_celery_exception

from asset_tracker.notify import next_calibration_notification

logger = get_task_logger(__name__)


def get_session_factory():
    """Create an SQLAlchemy session factory.

    Returns:
        sqlalchemy.orm.sessionmaker.

    """
    sqlalchemy_url = app.conf.pyramid_config['app:main']['sqlalchemy.url']
    engine = create_engine(sqlalchemy_url)
    return models.get_session_factory(engine)


@app.task()
def next_calibration_reminder(validity_months=3):
    """Remind the assets owner about planned calibration.

    Args:
        validity_months (int) reminder period before calibration.

    """
    mandatory_config = ('asset_tracker.cloud_name', 'asset_tracker.server_url',
                        'rta.client_id', 'rta.secret', 'rta.server_url')

    try:
        # Validate all mandatory config is present.
        [app.conf.pyramid_config['app:main'][config] for config in mandatory_config]
    except AttributeError as error:
        sentry_celery_exception(app.conf)
        logger.error(error)
        return -1

    # To avoid Jan (28,29,30,31) + 1 month = Feb 28, convert months in days.
    expiration_date = arrow.utcnow().shift(days=validity_months * 30).format('YYYY-MM-DD')

    # Set up db connection.
    session_factory = get_session_factory()

    with transaction.manager:
        db_session = models.get_tm_session(session_factory, transaction.manager)

        # Checkups about to expire on expiration_date.
        assets = db_session.query(models.Asset) \
            .filter(models.Asset.calibration_next == expiration_date) \
            .order_by(models.Asset.tenant_id) \
            .all()

        if assets:
            pyramid_config = app.conf.pyramid_config['app:main']

            # must be sorted by tenant_id
            groupby_tenant = itertools.groupby(assets, key=lambda asset: asset.tenant_id)

            for tenant_id, assets in groupby_tenant:
                next_calibration_notification(pyramid_config, tenant_id, list(assets), validity_months, expiration_date)
