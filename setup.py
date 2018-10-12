"""Gab.com API client setup."""


import io
import re
import sys

from setuptools import setup
from setuptools.command.test import test as TestCommand


def find_version(filename):
    """Uses re to pull out the assigned value to __version__ in filename."""

    with io.open(filename, encoding="utf-8") as version_file:
        version_match = re.search(r'^__version__ = [\'"]([^\'"]*)[\'"]',
                                  version_file.read(), re.M)
    if version_match:
        return version_match.group(1)
    return "0.0-version-unknown"


def read_description(filename):
    """Reads filename and returns its contents."""

    with io.open(filename, encoding="utf-8") as opendescription:
        return opendescription.read()


class PyTest(TestCommand):
    """Shim in pytest to be able to use it with setup.py test."""

    def finalize_options(self):
        """Stolen from http://pytest.org/latest/goodpractises.html."""

        TestCommand.finalize_options(self)
        self.test_args = ["-v", "-rf", "--cov-report", "term-missing", "--cov",
                          "gab", "tests"]
        self.test_suite = True

    def run_tests(self):
        """Also shamelessly stolen."""

        # have to import here, outside the eggs aren't loaded
        import pytest
        errno = pytest.main(self.test_args)
        raise SystemExit(errno)


setup(
    name="gab",
    version=find_version("gab.py"),
    author="Adam Talsma",
    author_email="adam@talsma.ca",
    py_modules=["gab"],
    install_requires=[
        "requests >= 2.19.1",
        "beautifulsoup4 >= 4.6.3",
    ],
    extras_require={
        ":python_version < '3.7'": "dataclasses >= 0.6",
    },
    url="https://github.com/a-tal/gab",
    description="Python client library for the Gab.com API",
    long_description=read_description("README.md"),
    download_url="https://github.com/a-tal/gab",
    tests_require=["pytest", "pytest-cov"],
    cmdclass={"test": PyTest},
    license="MIT",
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
)
