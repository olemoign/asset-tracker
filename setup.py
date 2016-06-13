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
    'python-dateutil',
    'SQLAlchemy',
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
    test_suite='asset_tracker',
    install_requires=requires,
    extras_require={
        'testing': tests_require,
    },
    dependency_links={
        'git+https://github.com/Parsys-Telemedicine/py-openid-connect.git#egg=py_openid_connect',
    },
    entry_points="""\
    [paste.app_factory]
    main = asset_tracker:main
    """,
)
