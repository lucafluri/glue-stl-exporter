#!/usr/bin/env python

from __future__ import print_function

from setuptools import setup, find_packages

entry_points = """
[glue.plugins]
stlexporter=stlexporter:setup
"""

with open('README.rst') as infile:
    LONG_DESCRIPTION = infile.read()

with open('stlexporter/version.py') as infile:
    exec(infile.read())

setup(name='stlexporter',
      version=__version__,
      description='STL Exporter',
      long_description=LONG_DESCRIPTION,
      url="https://github.com/tbd",
      author='',
      author_email='',
      packages = find_packages(),
      package_data={},
      entry_points=entry_points
    )