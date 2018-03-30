import os
import subprocess

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.txt')) as f:
    README = f.read()
with open(os.path.join(here, 'CHANGES.txt')) as f:
    CHANGES = f.read()

requires = [
    'alembic',
    'parsys_utilities',
    'paste',
    'plaster_pastedeploy',
    'pyramid',
    'pyramid_assetviews',
    'pyramid_jinja2',
    'pyramid_redis_sessions',
    'pyramid_tm',
    'python-dateutil',
    'raven',
    'setuptools',
    'sqlalchemy',
    'transaction',
    'waitress',
    'zope.sqlalchemy',
]

optional = {
    'dev': [
        'babel',
        'pybabel-json',
        'pyramid_debugtoolbar',
    ],
    'prod': [
        'psycopg2-binary',
    ],
    'qa': [
        'flake8',
    ]
}

get_version = 'git describe --match "[0-9]*.[0-9]*" --tags --dirty | sed -e "s/-/+/"'
version = subprocess.check_output(get_version, shell=True).decode('ascii').strip()

setup(
    name='asset_tracker',
    version=version,
    description='Asset Tracker',
    long_description=README + '\n\n' + CHANGES,
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Pyramid',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
        'Programming Language :: Python :: 3.5',
        'License :: Other/Proprietary License',
    ],
    author='Parsys',
    author_email='info@parsys.com',
    url='https://parsys.com',
    keywords='web pyramid pylons',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=requires,
    extras_require=optional,
    entry_points={
        'paste.app_factory': [
            'main = asset_tracker:main',
        ],
    },
)
