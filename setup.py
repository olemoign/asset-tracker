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
    'ndg-httpsclient',
    'newrelic',
    'oauthlib',
    'Paste',
    'pyasn1',
    'PyJWT',
    'pyOpenSSL',
    'pyramid',
    'pyramid_assetviews',
    'pyramid_debugtoolbar',
    'pyramid_jinja2',
    'pyramid_tm',
    'pytest',
    'requests',
    'SQLAlchemy',
    'transaction',
    'zope.sqlalchemy',
    'waitress',
]

setup(name='tracking',
      version='0.1',
      description='tracking',
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
      test_suite='tracking',
      install_requires=requires,
      entry_points="""\
      [paste.app_factory]
      main = tracking:main
      [console_scripts]
      initialize_tracking_db = tracking.scripts.initializedb:main
      """,
)
