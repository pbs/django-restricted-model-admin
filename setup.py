#!/usr/bin/env python
import os
from setuptools import setup, find_packages

README_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                           'README.rst')

dependencies = [
    'django>=1.4.1, <1.5',
]

setup(
    name='django-restricted-model-admin',
    version='0.1',
    description='Extend ModelAdmin classes',
    long_description=open(README_PATH, 'r').read(),
    author='3PG',
    author_email='',
    url='https://github.com/pbs/django-restricted-model-admin',
    packages=find_packages(),
    include_package_data=True,
    install_requires=dependencies,
    setup_requires=[
        's3sourceuploader',
    ],
    tests_require=[
        'django-nose',
        'mock==1.0.1',
        'django-cms<2.3.6'
    ],
    test_suite='runtests.runtests',
)
