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
    'pastescript',
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
    description='asset_tracker',
    long_description=README + '\n\n' + CHANGES,
    classifiers=[
        "Programming Language :: Python",
        "Framework :: Pyramid",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
    ],
    author='',
    author_email='',
    url='',
    keywords='web wsgi bfg pylons pyramid',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=True,
    install_requires=requires,
    extras_require=optional,
    entry_points="""\
    [paste.app_factory]
    main = asset_tracker:main
    """,
)
