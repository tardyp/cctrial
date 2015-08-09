#!/usr/bin/env python
#
"""
Standard setup script.
"""
from setuptools import setup
import os

README = open(os.path.join(os.path.dirname(__file__), "README.rst")).read()

setup(
    name="cctrial",
    version="1.0.2",
    description="continous trial runner",
    long_description=README,
    author="Pierre Tardy",
    author_email="tardyp@gmail.com",
    license="MIT",
    packages=["cctrial"],
    entry_points={
        'console_scripts': [
            'cctrial=cctrial.cctrial:main',
        ],
    },
    install_requires=[
        'twisted >= 15.0.0',
        'argh',
        'watchdog'
    ]
)
