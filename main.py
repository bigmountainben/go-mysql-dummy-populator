#!/usr/bin/env python3
"""
MySQL Database Populator

A tool to populate MySQL databases with dummy data, handling foreign keys,
circular dependencies, and many-to-many relationships.
"""

import os
import sys
import logging
import argparse
from db_connector import DatabaseConnector
from schema_analyzer import SchemaAnalyzer
from data_generator import DataGenerator
from populator import DatabasePopulator
from utils import (
    setup_logging, load_environment_variables, get_env_int, print_summary,
    validate_connection_params, print_schema_analysis, verify_table_population,
    print_verification_results
)

def parse_arguments():
    """
    Parse command line arguments

    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(description='Populate MySQL database with dummy data')

    parser.add_argument('--host', help='MySQL host (default: from MYSQL_HOST env var)')
    parser.add_argument('--user', help='MySQL user (default: from MYSQL_USER env var)')
    parser.add_argument('--password', help='MySQL password (default: from MYSQL_PASSWORD env var)')
    parser.add_argument('--database', help='MySQL database name (default: from MYSQL_DATABASE env var)')
    parser.add_argument('--port', help='MySQL port (default: from MYSQL_PORT env var or 3306)')
    parser.add_argument('--records', type=int, help='Number of records per table (default: from MYSQL_RECORDS env var or 10)')
    parser.add_argument('--locale', help='Locale for fake data generation (default: from MYSQL_LOCALE env var or en_US)')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help='Log level (default: from MYSQL_LOG_LEVEL env var or INFO)')
    parser.add_argument('--env-file', default='.env', help='Path to .env file (default: .env)')
    parser.add_argument('--analyze-only', action='store_true',
                        help='Only analyze the database schema without populating data')
    parser.add_argument('--verify', action='store_true',
                        help='Verify that all tables have at least one record after population')
    parser.add_argument('--min-records', type=int, default=1,
                        help='Minimum number of records each table should have during verification (default: 1)')

    return parser.parse_args()

def main():
    """
    Main function
    """
    # Parse command line arguments
    args = parse_arguments()

    # Setup logging first (with basic configuration)
    setup_logging(args.log_level)

    # Load environment variables
    if not load_environment_variables(args.env_file):
        logging.warning("Some required environment variables are missing. Check your .env file or environment settings.")
        # Continue execution as command line arguments might provide the missing values

    # Get configuration from environment variables or command line arguments
    host = args.host or os.getenv('MYSQL_HOST')
    user = args.user or os.getenv('MYSQL_USER')
    password = args.password or os.getenv('MYSQL_PASSWORD')
    database = args.database or os.getenv('MYSQL_DATABASE')
    port = args.port or os.getenv('MYSQL_PORT', '3306')
    records = args.records or get_env_int('MYSQL_RECORDS', 10)
    locale = args.locale or os.getenv('MYSQL_LOCALE', 'en_US')

    # Validate connection parameters
    if not validate_connection_params(host, user, password, database, port):
        logging.error("Missing or invalid database connection parameters")
        logging.info("You can provide these via:")
        logging.info("1. Command line arguments (--host, --user, etc.)")
        logging.info("2. Environment variables (MYSQL_HOST, MYSQL_USER, etc.)")
        logging.info("3. A .env file (default: .env, or specify with --env-file)")
        logging.info("Run with --help for more information")
        sys.exit(1)

    logging.info(f"Starting MySQL database populator")
    logging.info(f"Database: {database} on {host}:{port}")
    logging.info(f"Records per table: {records}")

    try:
        # Initialize components
        db_connector = DatabaseConnector(host, user, password, database, port)

        if not db_connector.connect():
            logging.error("Failed to connect to the database")
            sys.exit(1)

        schema_analyzer = SchemaAnalyzer(db_connector)
        data_generator = DataGenerator(locale, schema_analyzer=schema_analyzer)
        populator = DatabasePopulator(db_connector, schema_analyzer, data_generator, records)

        # Analyze schema
        logging.info("Analyzing database schema...")
        if not schema_analyzer.analyze_schema():
            logging.error("Failed to analyze database schema")
            sys.exit(1)

        # Get tables
        tables = schema_analyzer.tables
        logging.info(f"Found {len(tables)} tables in the database")

        # Check if we're in analyze-only mode
        if args.analyze_only:
            logging.info("Analyze-only mode: Generating schema analysis report...")
            print_schema_analysis(schema_analyzer)
            logging.info("Schema analysis complete")
            sys.exit(0)

        # Populate database
        logging.info("Starting database population...")
        success = populator.populate_database()

        # Print summary
        successful_tables = [table for table in tables if table not in populator.failed_tables]
        failed_tables = list(populator.failed_tables)

        print_summary(tables, records, successful_tables, failed_tables)

        # Verify table population if requested
        verification_success = True
        if args.verify:
            verification_success, empty_tables, partially_populated_tables = verify_table_population(
                db_connector, tables, args.min_records
            )
            print_verification_results(empty_tables, partially_populated_tables, args.min_records)

        # Return appropriate exit code
        if not success or (args.verify and not verification_success):
            sys.exit(1)

    except Exception as e:
        logging.error(f"An error occurred: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # Clean up
        if 'db_connector' in locals() and db_connector:
            db_connector.disconnect()

    logging.info("Database population completed successfully")
    sys.exit(0)

if __name__ == "__main__":
    main()
