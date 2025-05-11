import os
import sys
import unittest
import mysql.connector
from mysql.connector import Error

# Add the parent directory to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_connector import DatabaseConnector
from populator import DatabasePopulator
from schema_analyzer import SchemaAnalyzer
from data_generator import DataGenerator

# Test configuration
TEST_DB_HOST = os.environ.get('MYSQL_HOST', 'localhost')
TEST_DB_USER = os.environ.get('MYSQL_USER', 'root')
TEST_DB_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
TEST_DB_NAME = os.environ.get('MYSQL_DATABASE', 'test_spatial_db')
TEST_SCHEMA_FILE = os.path.join(os.path.dirname(__file__), "schemas", "spatial_schema.sql")
NUM_RECORDS = 5

@unittest.skipIf(
    not os.environ.get('MYSQL_HOST') or
    not os.environ.get('MYSQL_USER') or
    not os.environ.get('MYSQL_PASSWORD') or
    not os.environ.get('MYSQL_DATABASE'),
    'Missing database connection parameters. Set MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, and MYSQL_DATABASE environment variables.'
)
class TestSpatialData(unittest.TestCase):
    """Test cases for spatial data types"""

    @classmethod
    def setUpClass(cls):
        """Set up the test database with the spatial schema"""
        # Create a new database for testing
        try:
            conn = mysql.connector.connect(
                host=TEST_DB_HOST,
                user=TEST_DB_USER,
                password=TEST_DB_PASSWORD
            )
            cursor = conn.cursor()

            # Drop the database if it exists
            cursor.execute(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}")

            # Create the database
            cursor.execute(f"CREATE DATABASE {TEST_DB_NAME}")

            conn.close()

            # Connect to the new database
            conn = mysql.connector.connect(
                host=TEST_DB_HOST,
                user=TEST_DB_USER,
                password=TEST_DB_PASSWORD,
                database=TEST_DB_NAME
            )
            cursor = conn.cursor()

            # Read and execute the schema file
            with open(TEST_SCHEMA_FILE, 'r') as f:
                schema_sql = f.read()

            # Split the schema into individual statements and execute them
            for statement in schema_sql.split(';'):
                if statement.strip():
                    cursor.execute(statement)

            conn.commit()
            conn.close()

            # Create a DatabaseConnector instance for the test
            cls.db = DatabaseConnector(TEST_DB_HOST, TEST_DB_USER, TEST_DB_PASSWORD, TEST_DB_NAME)

            # Create a SchemaAnalyzer instance
            schema = SchemaAnalyzer(cls.db)

            # Create a DataGenerator instance
            data_gen = DataGenerator('en_US', schema_analyzer=schema)

            # Create a DatabasePopulator instance
            populator = DatabasePopulator(cls.db, schema, data_gen, NUM_RECORDS)

            # Populate the database
            populator.populate_database()

        except Error as e:
            raise unittest.SkipTest(f"Failed to set up test database: {e}")

    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests"""
        # Cleanup
        if hasattr(cls, 'db'):
            cls.db.disconnect()

        # Drop the test database
        try:
            conn = mysql.connector.connect(
                host=TEST_DB_HOST,
                user=TEST_DB_USER,
                password=TEST_DB_PASSWORD
            )
            cursor = conn.cursor()
            cursor.execute(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}")
            conn.close()
        except Error as e:
            print(f"Warning: Failed to drop test database: {e}")

    def test_regions_spatial_data(self):
        """Test that the regions table has valid spatial data"""
        # Query the regions table
        query = "SELECT region_id, region_name, ST_AsText(boundary) AS boundary FROM regions"
        result = self.db.execute_query(query)

        # Check that we have the expected number of records
        self.assertGreaterEqual(len(result), NUM_RECORDS)

        # Check that the boundary column contains valid POLYGON data
        for row in result:
            self.assertTrue(row['boundary'].startswith('POLYGON(('))
            self.assertTrue(row['boundary'].endswith('))'))

    def test_cities_spatial_data(self):
        """Test that the cities table has valid spatial data"""
        # Query the cities table
        query = "SELECT city_id, city_name, ST_AsText(location) AS location, ST_AsText(boundary) AS boundary FROM cities"
        result = self.db.execute_query(query)

        # Check that we have the expected number of records
        self.assertGreaterEqual(len(result), NUM_RECORDS)

        # Check that the location column contains valid POINT data
        for row in result:
            self.assertTrue(row['location'].startswith('POINT('))
            self.assertTrue(row['location'].endswith(')'))

            # Check that the boundary column contains valid POLYGON data
            self.assertTrue(row['boundary'].startswith('POLYGON(('))
            self.assertTrue(row['boundary'].endswith('))'))

    def test_customers_spatial_data(self):
        """Test that the customers table has valid spatial data"""
        # Query the customers table
        query = "SELECT customer_id, customer_name, ST_AsText(location) AS location FROM customers"
        result = self.db.execute_query(query)

        # Check that we have the expected number of records
        self.assertGreaterEqual(len(result), NUM_RECORDS)

        # Check that the location column contains valid POINT data
        for row in result:
            self.assertTrue(row['location'].startswith('POINT('))
            self.assertTrue(row['location'].endswith(')'))

    def test_points_of_interest_spatial_data(self):
        """Test that the points_of_interest table has valid spatial data"""
        # Query the points_of_interest table
        query = "SELECT poi_id, poi_name, ST_AsText(location) AS location FROM points_of_interest"
        result = self.db.execute_query(query)

        # Check that we have the expected number of records
        self.assertGreaterEqual(len(result), NUM_RECORDS)

        # Check that the location column contains valid POINT data
        for row in result:
            self.assertTrue(row['location'].startswith('POINT('))
            self.assertTrue(row['location'].endswith(')'))

    def test_stores_spatial_data(self):
        """Test that the stores table has valid spatial data"""
        # Query the stores table
        query = "SELECT store_id, store_name, ST_AsText(location) AS location FROM stores"
        result = self.db.execute_query(query)

        # Check that we have the expected number of records
        self.assertGreaterEqual(len(result), NUM_RECORDS)

        # Check that the location column contains valid POINT data
        for row in result:
            self.assertTrue(row['location'].startswith('POINT('))
            self.assertTrue(row['location'].endswith(')'))

    def test_delivery_routes_spatial_data(self):
        """Test that the delivery_routes table has valid spatial data"""
        # Query the delivery_routes table
        query = "SELECT route_id, route_name, ST_AsText(route_path) AS route_path FROM delivery_routes"
        result = self.db.execute_query(query)

        # Check that we have the expected number of records
        self.assertGreaterEqual(len(result), NUM_RECORDS)

        # Check that the route_path column contains valid LINESTRING data
        for row in result:
            self.assertTrue(row['route_path'].startswith('LINESTRING('))
            self.assertTrue(row['route_path'].endswith(')'))

    def test_service_areas_spatial_data(self):
        """Test that the service_areas table has valid spatial data"""
        # Query the service_areas table
        query = "SELECT service_area_id, service_level, ST_AsText(boundary) AS boundary FROM service_areas"
        result = self.db.execute_query(query)

        # Check that we have the expected number of records
        self.assertGreaterEqual(len(result), NUM_RECORDS)

        # Check that the boundary column contains valid POLYGON data
        for row in result:
            self.assertTrue(row['boundary'].startswith('POLYGON(('))
            self.assertTrue(row['boundary'].endswith('))'))

    def test_customer_visits_spatial_data(self):
        """Test that the customer_visits table has valid spatial data"""
        # Query the customer_visits table
        query = "SELECT visit_id, ST_AsText(entry_point) AS entry_point FROM customer_visits"
        result = self.db.execute_query(query)

        # Check that we have the expected number of records
        self.assertGreaterEqual(len(result), NUM_RECORDS)

        # Check that the entry_point column contains valid POINT data
        for row in result:
            self.assertTrue(row['entry_point'].startswith('POINT('))
            self.assertTrue(row['entry_point'].endswith(')'))


if __name__ == '__main__':
    unittest.main()
