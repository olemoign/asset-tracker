import subprocess
from pathlib import Path

from setuptools import find_packages, setup

here = Path(__file__).resolve().parent
with open(here / 'README.txt') as f:
    README = f.read()
with open(here / 'CHANGES.txt') as f:
    CHANGES = f.read()

requires = [
    'alembic',
    'arrow',
    'celery[redis]==4.4.7',
    'filedepot',
    'jinja2',
    'parsys-utilities',
    'paste',
    'plaster-pastedeploy',
    'psycopg2-binary',
    'pyramid',
    'pyramid-assetviews',
    'pyramid-jinja2',
    'pyramid-session-redis',
    'pyramid-tm',
    'python-dateutil',
    'sentry-sdk',
    'setuptools',
    'sqlalchemy',
    'transaction',
    'waitress',
    'webob',
    'zope.sqlalchemy',
]

optional = {
    'dev': [
        'babel',
        'pybabel-json-md',
        'pyramid-debugtoolbar',
    ],
    'qa': [
        'flake8',
    ],
    'tests': [
        'pytest',
        'pytest-cov',
        'webtest',
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
        'Programming Language :: Python',
        'Framework :: Pyramid',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
        'Programming Language :: Python :: 3.6',
        'License :: Other/Proprietary License',
    ],
    author='Parsys',
    author_email='info@parsys.com',
    url='https://parsys.com',
    keywords='web pyramid pylons',
    packages=find_packages(exclude=['asset_tracker.tests']),
    include_package_data=True,
    zip_safe=False,
    python_requires='>=3.6',
    install_requires=requires,
    tests_require=optional['tests'],
    extras_require=optional,
    entry_points={
        'paste.app_factory': [
            'main = asset_tracker:main',
        ],
        'console_scripts': [
            'parsys_healthcheck = parsys_utilities.status:healthcheck'
        ],
    },
)
