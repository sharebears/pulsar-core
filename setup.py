#!/usr/bin/env python3
import sys

from setuptools import setup
from setuptools.command.test import test as TestCommand


class PyTest(TestCommand):
    user_options = [('pytest-args=', 'a', "Arguments to pass to py.test")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = []

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(self.pytest_args)
        sys.exit(errno)


setup(
    name='pulsar-core',
    version='0.0.2',
    description='A bittorrent indexer written in Flask.',
    long_description=open('README.rst').read(),
    long_description_content_type='text/markdown',
    license='MIT',
    author='sharebears',
    author_email='sharebears@tutanota.de',
    url='https://github.com/sharebears',
    packages=[
        'pulsar',
    ],
    include_package_data=True,
    python_requires='==3.7',
    tests_require=['pytest'],
    cmdclass={'test': PyTest},
    install_requires=[
        'blinker',
        'flask',
        'flask-cors',
        'flask-migrate',
        'flask-sqlalchemy',
        'psycopg2-binary',
        'redis',
        'voluptuous',
    ],
)
