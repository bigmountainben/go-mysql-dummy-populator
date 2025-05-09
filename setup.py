#!/usr/bin/env python3
"""
Setup script for mysql-dummy-populator
"""

import os
from setuptools import setup, find_packages

# Define version directly
version = '0.1.0'

# Read the long description from README.md
with open('README.md', 'r') as f:
    long_description = f.read()

# Get requirements from requirements.txt
with open('requirements.txt', 'r') as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name='mysql-dummy-populator',
    version=version,
    description='A tool to populate MySQL databases with realistic dummy data',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Slava Vitebski',
    author_email='slava@redislabs.com',
    url='https://github.com/vitebski/mysql-dummy-populator',
    packages=find_packages(include=['']),
    py_modules=[
        'db_connector',
        'schema_analyzer',
        'data_generator',
        'populator',
        'utils',
        'main'
    ],
    install_requires=requirements,
    python_requires='>=3.8',
    entry_points={
        'console_scripts': [
            'mysql-dummy-populator=main:main',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: Database Administrators',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: Database',
        'Topic :: Software Development :: Testing',
        'Topic :: Utilities',
    ],
    keywords='mysql, database, dummy data, testing, development',
    project_urls={
        'Bug Reports': 'https://github.com/vitebski/mysql-dummy-populator/issues',
        'Source': 'https://github.com/vitebski/mysql-dummy-populator',
    },
)
