import subprocess
from pathlib import Path

from setuptools import find_packages, setup

here = Path(__file__).resolve().parent
with open(here / 'README.md') as f:
    README = f.read()
with open(here / 'CHANGES.md') as f:
    CHANGES = f.read()

parsys_utilities = 'https://tracker.parsys.com/api/v4/projects/9/packages/pypi/files/ea8255c0f40c5ebe73d8298d1b4446330b0be483ce0e434aaf45cdf892d4ff62/parsys_utilities-3.6.0-py3-none-any.whl'  # noqa: E501
requires = [
    'alembic',
    'arrow',
    'celery[redis]',
    'filedepot',
    'importlib-resources',
    'jinja2',
    f'parsys-utilities @ {parsys_utilities}',
    'paste',
    'plaster-pastedeploy',
    'psycopg2-binary',
    'pyramid==1.10.8',
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
        'Programming Language :: Python :: 3.8',
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
            'parsys_healthcheck = parsys_utilities.status:healthcheck'
        ],
    },
)
