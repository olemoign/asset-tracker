import subprocess
from pathlib import Path

from setuptools import find_packages, setup

here = Path(__file__).resolve().parent
with open(here / 'README.md') as f:
    README = f.read()
with open(here / 'CHANGES.md') as f:
    CHANGES = f.read()

tracker = 'https://tracker.parsys.com/api/v4/projects/9/packages/pypi/files'
parsys_utilities_3_6_0 = f'{tracker}/ea8255c0f40c5ebe73d8298d1b4446330b0be483ce0e434aaf45cdf892d4ff62/parsys_utilities-3.6.0-py3-none-any.whl'  # noqa: E501
requires = [
    'alembic==1.6.3',
    'arrow==1.1.0',
    'celery[redis]==5.1.0',
    'filedepot==0.8.0',
    'importlib-resources==5.1.4',
    'jinja2==3.0.1',
    f'parsys-utilities @ {parsys_utilities_3_6_0}',
    'paste==3.5.0',
    'plaster-pastedeploy==0.7',
    'psycopg2-binary==2.8.6',
    'pyramid==1.10.8',
    'pyramid-assetviews==1.0a3',
    'pyramid-jinja2==2.8',
    'pyramid-session-redis==1.6.1',
    'pyramid-tm==2.4',
    'python-dateutil==2.8.1',
    'sentry-sdk==1.1.0',
    'setuptools==57.0.0',
    'sqlalchemy==1.4.15',
    'transaction==3.0.1',
    'waitress==2.0.0',
    'webob==1.8.7',
    'zope.sqlalchemy==1.4',
]

optional = {
    'dev': [
        'babel==2.9.1',
        'pybabel-json-md==0.1.0',
        'pyramid-debugtoolbar==4.9',
    ],
    'qa': [
        'flake8==3.9.2',
    ],
    'tests': [
        'pytest==6.2.4',
        'pytest-cov==2.12.0',
        'webtest==2.0.35',
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
    tests_require=optional['tests'],
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
