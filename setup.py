#!/usr/bin/env python
#
"""
Standard setup script.
"""
from setuptools import setup


setup(
    name="cctrial",
    version="1.0.0",
    description="continous trial runner",
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
