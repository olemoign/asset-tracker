import subprocess
from pathlib import Path

from setuptools import find_packages, setup

here = Path(__file__).resolve().parent
with open(here / 'README.md') as f:
    README = f.read()
with open(here / 'CHANGES.md') as f:
    CHANGES = f.read()

tracker = 'https://tracker.parsys.com/api/v4/projects/9/packages/pypi/files'
parsys_utilities_4_0_2 = f'{tracker}/7cdd88b326cd28a344d3a86727383db4fe61bce186d5be3eb6230d1b592c17cf/parsys_utilities-4.0.2-py3-none-any.whl'  # noqa: E501
requires = [
    'alembic==1.7.4',
    'arrow==1.2.1',
    'celery[redis]==5.1.2',
    'filedepot==0.8.0',
    'jinja2==3.0.2',
    f'parsys-utilities @ {parsys_utilities_4_0_2}',
    'paste==3.5.0',
    'plaster-pastedeploy==0.7',
    'psycopg2-binary==2.9.1',
    'pyramid==2.0',
    'pyramid-assetviews==1.0a3',
    'pyramid-jinja2==2.8',
    'pyramid-session-redis==1.6.2',
    'pyramid-tm==2.4',
    'python-dateutil==2.8.2',
    'sentry-sdk==1.4.3',
    'setuptools==58.3.0',
    'sqlalchemy==1.4.26',
    'transaction==3.0.1',
    'waitress==2.0.0',
    'webob==1.8.7',
    'zope.sqlalchemy==1.6',
]

optional = {
    'dev': [
        'babel==2.9.1',
        'pybabel-json-md==0.1.0',
        'pyramid-debugtoolbar==4.9',
    ],
    'qa': [
        'flake8==4.0.1',
    ],
    'tests': [
        'pytest==6.2.5',
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
