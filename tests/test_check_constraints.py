#!/usr/bin/env python3
"""
Test script for check constraint handling
"""

import unittest
import logging
import os
import re
import sys

# Add the parent directory to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_connector import DatabaseConnector
from schema_analyzer import SchemaAnalyzer
from data_generator import DataGenerator

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TestCheckConstraints(unittest.TestCase):
    """Test cases for check constraint handling"""

    @classmethod
    def setUpClass(cls):
        """Set up test environment once before all tests"""
        # Get database connection parameters from environment variables
        cls.host = os.getenv('MYSQL_HOST')
        cls.user = os.getenv('MYSQL_USER')
        cls.password = os.getenv('MYSQL_PASSWORD')
        cls.database = os.getenv('MYSQL_DATABASE')
        cls.port = os.getenv('MYSQL_PORT', '3306')

        # Skip tests if database connection parameters are missing
        if not all([cls.host, cls.user, cls.password, cls.database]):
            raise unittest.SkipTest(
                "Missing database connection parameters. Set MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, and MYSQL_DATABASE environment variables."
            )

        # Initialize components
        cls.db_connector = DatabaseConnector(cls.host, cls.user, cls.password, cls.database, cls.port)

        # Connect to the database
        if not cls.db_connector.connect():
            raise unittest.SkipTest("Failed to connect to the database")

        # Initialize schema analyzer
        cls.schema_analyzer = SchemaAnalyzer(cls.db_connector)

        # Analyze schema
        logging.info("Analyzing database schema...")
        if not cls.schema_analyzer.analyze_schema():
            raise unittest.SkipTest("Failed to analyze database schema")

        # Initialize data generator
        cls.data_generator = DataGenerator(locale='en_US', schema_analyzer=cls.schema_analyzer)

    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests"""
        if hasattr(cls, 'db_connector') and cls.db_connector:
            cls.db_connector.disconnect()

    def test_check_constraint_extraction(self):
        """Test the extraction and parsing of check constraints"""
        # Check if check constraints were extracted
        self.assertTrue(hasattr(self.schema_analyzer, 'check_constraints'),
                        "Schema analyzer does not have check_constraints attribute")

        # Skip test if no check constraints found
        if not self.schema_analyzer.check_constraints:
            self.skipTest("No check constraints found in the database")

        # Print extracted check constraints for debugging
        logging.info("Extracted check constraints:")
        for table, constraints in self.schema_analyzer.check_constraints.items():
            logging.info(f"Table: {table}")
            for constraint in constraints:
                logging.info(f"  - {constraint['constraint_name']}: {constraint['raw_clause']}")
                logging.info(f"    Type: {constraint['type']}")
                logging.info(f"    Column: {constraint['column']}")
                if constraint['min_value'] is not None:
                    logging.info(f"    Min value: {constraint['min_value']}")
                if constraint['max_value'] is not None:
                    logging.info(f"    Max value: {constraint['max_value']}")
                if constraint['allowed_values'] is not None:
                    logging.info(f"    Allowed values: {constraint['allowed_values']}")

        # Verify that at least one constraint was extracted
        self.assertGreater(
            sum(len(constraints) for constraints in self.schema_analyzer.check_constraints.values()),
            0,
            "No check constraints were extracted"
        )

        # Verify that the DefaultRedisFlexRamRatio constraint was extracted correctly
        found_special_constraint = False
        for table, constraints in self.schema_analyzer.check_constraints.items():
            for constraint in constraints:
                if constraint['constraint_name'] == 'check_DefaultRedisFlexRamRatio':
                    found_special_constraint = True
                    self.assertEqual(constraint['type'], 'between',
                                    "DefaultRedisFlexRamRatio constraint should be of type 'between'")
                    self.assertEqual(constraint['column'], 'DefaultRedisFlexRamRatio',
                                    "Column name should be 'DefaultRedisFlexRamRatio'")

        # Skip this assertion if the database doesn't have this specific constraint
        if 'Cluster' in self.schema_analyzer.check_constraints:
            self.assertTrue(found_special_constraint,
                           "DefaultRedisFlexRamRatio constraint not found or not correctly parsed")

    def test_value_generation_with_constraints(self):
        """Test the generation of values that respect check constraints"""
        # Skip test if no check constraints found
        if not hasattr(self.schema_analyzer, 'check_constraints') or not self.schema_analyzer.check_constraints:
            self.skipTest("No check constraints found in the database")

        # Test value generation for tables with check constraints
        for table, constraints in self.schema_analyzer.check_constraints.items():
            logging.info(f"Testing value generation for table: {table}")

            # Get column information for the table
            columns_query = f"""
                SELECT
                    column_name, data_type, column_type, is_nullable,
                    column_key, extra, column_comment
                FROM
                    information_schema.columns
                WHERE
                    table_schema = %s AND table_name = %s
            """
            columns_result = self.db_connector.execute_query(columns_query, (self.database, table))
            self.assertIsNotNone(columns_result, f"Failed to retrieve columns for table {table}")

            # Test value generation for columns with check constraints
            for constraint in constraints:
                column_name = constraint['column']

                # Find the column info
                column_info = None
                for col in columns_result:
                    # Handle case sensitivity in column names
                    col_name = col.get('column_name', col.get('COLUMN_NAME'))
                    if col_name == column_name:
                        # Normalize column info keys to lowercase
                        normalized_col = {}
                        for key, value in col.items():
                            # Try both lowercase and uppercase versions of the key
                            normalized_key = key.lower()
                            normalized_col[normalized_key] = value
                        column_info = normalized_col
                        break

                if not column_info:
                    logging.warning(f"Column {column_name} not found in table {table}")
                    continue

                # Generate values and check if they respect the constraint
                logging.info(f"  Testing value generation for column: {column_name}")
                for i in range(10):  # Generate 10 values
                    value = self.data_generator.generate_value(column_info, table_name=table)
                    logging.info(f"    Generated value: {value}")

                    # Verify the value respects the constraint
                    if constraint['type'] in ('range', 'between') and constraint['min_value'] is not None and constraint['max_value'] is not None:
                        if value is not None:
                            try:
                                self.assertGreaterEqual(float(value), float(constraint['min_value']),
                                                      f"Value {value} is less than minimum {constraint['min_value']}")
                                self.assertLessEqual(float(value), float(constraint['max_value']),
                                                   f"Value {value} is greater than maximum {constraint['max_value']}")
                                logging.info(f"    Value {value} is within range {constraint['min_value']} to {constraint['max_value']}")
                            except (ValueError, TypeError) as e:
                                logging.error(f"    Validation error: {e}")

                    elif constraint['type'] == 'in' and constraint['allowed_values'] is not None:
                        if value is not None:
                            self.assertIn(value, constraint['allowed_values'],
                                         f"Value {value} is not in allowed values {constraint['allowed_values']}")
                            logging.info(f"    Value {value} is in allowed values {constraint['allowed_values']}")

                    elif constraint['type'] == 'equality' and constraint['allowed_values'] is not None:
                        if value is not None:
                            self.assertEqual(value, constraint['allowed_values'][0],
                                           f"Value {value} is not equal to {constraint['allowed_values'][0]}")
                            logging.info(f"    Value {value} equals required value {constraint['allowed_values'][0]}")

                    # For unknown constraints, try to extract BETWEEN pattern from raw clause
                    elif constraint['type'] == 'unknown' and constraint.get('raw_clause'):
                        raw_clause = constraint.get('raw_clause', '')
                        between_match = re.search(r'BETWEEN\s+(\d+\.?\d*)\s+AND\s+(\d+\.?\d*)', raw_clause, re.IGNORECASE)
                        if between_match and value is not None:
                            try:
                                float_value = float(value)
                                min_val = float(between_match.group(1))
                                max_val = float(between_match.group(2))
                                self.assertGreaterEqual(float_value, min_val, f"Value {value} is less than minimum {min_val}")
                                self.assertLessEqual(float_value, max_val, f"Value {value} is greater than maximum {max_val}")
                                logging.info(f"    Value {value} is within range {min_val} to {max_val} (extracted from raw clause)")
                            except (ValueError, TypeError) as e:
                                logging.error(f"    Validation error: {e}")

if __name__ == "__main__":
    unittest.main()
