import os

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
    'sqlalchemy',
    'transaction',
    'waitress',
    'zope.sqlalchemy',
]

dev_requires = [
    'babel',
    'pybabel-json',
    'pyramid_debugtoolbar',
]

prod_requires = [
    'psycopg2',
]

tests_require = [
    'mccabe',
    'pyflakes',
    'pylint',
    'pylint-mccabe',
    'vulture',
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
    tests_require=tests_require,
    extras_require={
        'dev': dev_requires,
        'prod': prod_requires,
        'testing': tests_require,
    },
    entry_points="""\
    [paste.app_factory]
    main = asset_tracker:main
    """,
)
