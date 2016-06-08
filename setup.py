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
    'inflection',
    'newrelic',
    'Paste',
    'PasteScript',
    'py_openid_connect',
    'psycopg2',
    'pyramid',
    'pyramid_assetviews',
    'pyramid_debugtoolbar',
    'pyramid_jinja2',
    'pyramid_tm',
    'SQLAlchemy',
    'transaction',
    'waitress',
    'zope.sqlalchemy',
]

setup(
    name='asset_tracker',
    version='0.1',
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
    zip_safe=False,
    test_suite='asset_tracker',
    install_requires=requires,
    entry_points="""\
    [paste.app_factory]
    main = asset_tracker:main
    [console_scripts]
    asset_tracker_initialize_db = asset_tracker.scripts.initializedb:main
    """,
)
