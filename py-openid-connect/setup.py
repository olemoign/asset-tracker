import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'requirements.txt')) as f:
    requires = f.read()

setup(
    name='py-openid-connect',
    version='0.9',
    description='py-openid-connect',
    classifiers=[
        "Programming Language :: Python",
        "Framework :: Pyramid",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
    ],
    author='Olivier Le Moign',
    author_email='olemoign@parsys.com',
    url='',
    keywords='web bfg pylons pyramid',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=requires,
)
