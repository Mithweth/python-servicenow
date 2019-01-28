#!/usr/bin/env python
from setuptools import setup
import servicenow.release

setup(
    name="python-servicenow",
    version=servicenow.release.__version__,
    description="ServiceNow module for Python",
    author="Jean-Baptiste LANGLOIS",
    author_email="jeanbaptiste.langlois@gmail.com",
    long_description="Module to access and handle ServiceNow queries",
    license="GPL",
    test_suite="tests",
    packages=['servicenow'],
)
