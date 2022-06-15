import subprocess
from pathlib import Path

from setuptools import find_packages, setup

here = Path(__file__).resolve().parent
with open(here / 'README.md') as f:
    README = f.read()
with open(here / 'CHANGES.md') as f:
    CHANGES = f.read()

requires = [
    'alembic==1.8.0',
    'arrow==1.2.2',
    'celery[redis]==5.2.7',
    'filedepot==0.8.0',
    'jinja2==3.1.2',
    'packaging==21.3',
    'parsys-utilities==4.2.14',
    'paste==3.5.0',
    'psycopg2==2.9.3',
    'pyramid==1.10.8',
    'pyramid-assetviews==1.0a3',
    'pyramid-jinja2==2.10.0',
    'pyramid-session-redis==1.6.3',
    'pyramid-tm==2.5',
    'python-dateutil==2.8.2',
    'sentry-sdk==1.5.12',
    'sqlalchemy==1.4.37',
    'transaction==3.0.1',
    'waitress==2.1.2',
    'zope.sqlalchemy==1.6',
]

optional = {
    'dev': [
        'babel==2.10.2',
        'pybabel-json-md==0.1.0',
        'pyramid-debugtoolbar==4.9',
    ],
    'qa': [
        'flake8==4.0.1',
    ],
    'tests': [
        'pytest==7.1.2',
        'pytest-cov==3.0.0',
        'webtest==3.0.0',
    ],
}

get_version = 'git describe --match "[0-9]*.[0-9]*" --tags --dirty | sed -e "s/-/+/"'
version = subprocess.check_output(get_version, shell=True).decode('ascii').strip()

setup(
    name='asset-tracker',
    version=version,
    description='Asset Tracker',
    long_description=f'{README}\n\n{CHANGES}',
    classifiers=[
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Framework :: Pyramid',
        'License :: Other/Proprietary License',
    ],
    author='Parsys',
    author_email='info@parsys.com',
    url='https://parsys.com',
    keywords='web pyramid pylons',
    packages=find_packages(exclude=['asset_tracker.tests']),
    include_package_data=True,
    python_requires='>=3.8',
    install_requires=requires,
    extras_require=optional,
    entry_points={
        'paste.app_factory': [
            'main = asset_tracker:main',
        ],
        'console_scripts': [
            'parsys_healthcheck = parsys_utilities.status:healthcheck',
        ],
    },
)
