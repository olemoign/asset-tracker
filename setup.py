import os
import subprocess

from setuptools import find_packages, setup

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.txt')) as f:
    README = f.read()
with open(os.path.join(here, 'CHANGES.txt')) as f:
    CHANGES = f.read()

requires = [
    'alembic',
    'arrow',
    'celery[redis]',
    'jinja2',
    'kombu',
    'parsys-utilities',
    'paste',
    'plaster-pastedeploy',
    'pyramid',
    'pyramid-assetviews',
    'pyramid-jinja2',
    'pyramid-session_redis',
    'pyramid-tm',
    'python-dateutil',
    'sentry-sdk',
    'setuptools',
    'sqlalchemy',
    'transaction',
    'waitress',
    'zope.sqlalchemy',
]

optional = {
    'dev': [
        'babel',
        'pybabel-json-md',
        'pyramid-debugtoolbar',
    ],
    'prod': [
        'psycopg2-binary',
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
    python_requires='>=3.5',
    install_requires=requires,
    tests_require=optional['tests'],
    extras_require=optional,
    entry_points={
        'paste.app_factory': [
            'main = asset_tracker:main',
        ],
    },
)
