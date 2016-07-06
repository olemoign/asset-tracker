import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.txt')) as f:
    README = f.read()
with open(os.path.join(here, 'CHANGES.txt')) as f:
    CHANGES = f.read()

requires = [
    'alembic',
    'babel',
    'kombu==3.0.34',
    'newrelic',
    'parsys_utilities',
    'paste',
    'pastescript',
    'psycopg2',
    'pyramid',
    'pyramid_assetviews',
    'pyramid_debugtoolbar',
    'pyramid_jinja2',
    'pyramid_redis_sessions',
    'pyramid_tm',
    'python-dateutil',
    'sqlalchemy',
    'transaction',
    'waitress',
    'zope.sqlalchemy',
]

tests_require = [
    'mccabe',
    'pylint',
    'pylint-mccabe',
    'vulture',
    'pyflakes',
]

setup(
    name='asset_tracker',
    version='2.6',
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
    dependency_links={
        'git+https://github.com/Parsys-Telemedicine/parsys_utilities.git#egg=parsys_utilities-1.0.0',
    },
    extras_require={
        'testing': tests_require,
    },
    entry_points="""\
    [paste.app_factory]
    main = asset_tracker:main
    """,
)
