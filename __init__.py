"""
MySQL Dummy Data Populator

A Python tool that populates MySQL databases with realistic dummy data,
handling foreign keys, circular dependencies, and many-to-many relationships.
"""

__version__ = '0.1.0'
__author__ = 'Slava Vitebski'
__email__ = 'slava@redislabs.com'

from .db_connector import DatabaseConnector
from .schema_analyzer import SchemaAnalyzer
from .data_generator import DataGenerator
from .populator import DatabasePopulator
from .utils import (
    setup_logging, load_environment_variables, get_env_int, print_summary,
    validate_connection_params, print_schema_analysis, verify_table_population,
    print_verification_results
)

__all__ = [
    'DatabaseConnector',
    'SchemaAnalyzer',
    'DataGenerator',
    'DatabasePopulator',
    'setup_logging',
    'load_environment_variables',
    'get_env_int',
    'print_summary',
    'validate_connection_params',
    'print_schema_analysis',
    'verify_table_population',
    'print_verification_results',
]
