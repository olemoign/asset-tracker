"""Data migration: add site_id

Fill new site column `site_id` with random_id

"""
from sqlalchemy import create_engine, Column, Unicode as String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound

from parsys_utilities.random import random_id

from asset_tracker.models import Site


# SQLITE = 'sqlite:////home/user/project_root/tmp/parsys_cloud.sqlite'
# PG_SQL = 'postgresql://user:password@localhost/postgres'
AT_DB_PATH = 'postgresql://abonamy:abonamy@localhost/at_dev'

ALEMBIC_VERSION = '70292af6fd9e'

Base = declarative_base()


# Add local Alembic table to check database version.
class TmpAlembicVersion(Base):
    __tablename__ = 'alembic_version'
    version_num = Column(String, primary_key=True)


def get_db_session(db_path):
    """Get SQLAlchemy session to query database.

    Args:
        db_path (str).

    Returns:
        db_session (sqlalchemy.orm.session.Session).

    """
    engine = create_engine(db_path)
    session_maker = sessionmaker(bind=engine)
    db_session = session_maker()

    return db_session


def check_db_state(db_session, alembic_version):
    """Verify that the database is in the expected state."""
    try:
        db_session.query(TmpAlembicVersion).filter_by(version_num=alembic_version).one()

    except NoResultFound as e:
        err_msg = 'The database expected state ({}) is not fulfilled.'.format(alembic_version)
        raise Exception(err_msg) from e


def get_sites(db_session):
    """Get sites without site_id."""
    sites = db_session.query(Site).filter(Site.site_id.is_(None))
    return sites


def data_migration():
    """Main function: fill the site_id column of site table."""
    # database connection
    at_db_session = get_db_session(AT_DB_PATH)

    # perform migration in a specific state
    check_db_state(at_db_session, ALEMBIC_VERSION)

    # add random id to site_id column
    sites = get_sites(at_db_session)

    i = 0
    for site in sites:
        site.site_id = random_id()
        at_db_session.commit()
        i += 1

    print('updated sites: {}'.format(i))


if __name__ == '__main__':
    data_migration()
