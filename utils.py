import os
import logging
import sys
import networkx as nx
from dotenv import load_dotenv

def setup_logging(log_level=None):
    """
    Set up logging configuration

    Args:
        log_level (str, optional): Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Get log level from environment variable or parameter
    level_str = log_level or os.getenv('MYSQL_LOG_LEVEL', 'INFO')

    # Map string to logging level
    level_map = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }

    level = level_map.get(level_str.upper(), logging.INFO)

    # Configure logging
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    logging.info(f"Logging configured with level: {level_str}")

def load_environment_variables(env_file='.env'):
    """
    Load environment variables from .env file

    Args:
        env_file (str, optional): Path to .env file

    Returns:
        bool: True if all required variables are present, False otherwise
    """
    # Check if a sample .env file exists but not the actual .env file
    if not os.path.exists(env_file) and os.path.exists(f"{env_file}.sample"):
        logging.info(f"No {env_file} file found, but {env_file}.sample exists. "
                    f"Consider copying {env_file}.sample to {env_file} and updating it.")

    # Load environment variables from .env file if it exists
    if os.path.exists(env_file):
        load_dotenv(env_file)
        logging.info(f"Loaded environment variables from {env_file}")
    else:
        logging.info(f"No {env_file} file found, using existing environment variables")

    # Check for required environment variables
    required_vars = ['MYSQL_HOST', 'MYSQL_USER', 'MYSQL_PASSWORD', 'MYSQL_DATABASE']
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        logging.warning(f"Missing required environment variables: {', '.join(missing_vars)}")
        logging.info("These can be provided via command line arguments, environment variables, or a .env file")
        return False

    # Log all available MySQL_* environment variables (for debugging)
    if logging.getLogger().level <= logging.DEBUG:
        mysql_vars = {k: v for k, v in os.environ.items() if k.startswith('MYSQL_')}
        # Mask password
        if 'MYSQL_PASSWORD' in mysql_vars:
            mysql_vars['MYSQL_PASSWORD'] = '********'
        logging.debug(f"Available MySQL environment variables: {mysql_vars}")

    return True

def get_env_int(var_name, default=None):
    """
    Get an integer value from environment variable

    Args:
        var_name (str): Environment variable name
        default (int, optional): Default value if not found or not convertible

    Returns:
        int: Value from environment variable or default
    """
    value = os.getenv(var_name)

    if value is None:
        return default

    try:
        return int(value)
    except ValueError:
        logging.warning(f"Environment variable {var_name} is not a valid integer: {value}")
        return default

def print_summary(tables, records_per_table, successful_tables, failed_tables):
    """
    Print a summary of the population process

    Args:
        tables (list): List of all tables
        records_per_table (int): Number of records per table
        successful_tables (list): List of successfully populated tables
        failed_tables (list): List of tables that failed to populate
    """
    total_tables = len(tables)
    total_successful = len(successful_tables)
    total_failed = len(failed_tables)
    total_records = total_successful * records_per_table

    print("\n" + "=" * 50)
    print("DATABASE POPULATION SUMMARY")
    print("=" * 50)
    print(f"Total tables processed: {total_tables}")
    print(f"Successfully populated tables: {total_successful}")
    print(f"Failed tables: {total_failed}")
    print(f"Total records inserted: {total_records}")

    if failed_tables:
        print("\nFailed tables:")
        for table in failed_tables:
            print(f"  - {table}")

    print("=" * 50)

def print_schema_analysis(schema_analyzer):
    """
    Print a detailed analysis of the database schema

    Args:
        schema_analyzer (SchemaAnalyzer): The schema analyzer instance with analyzed schema
    """
    tables = schema_analyzer.tables
    views = schema_analyzer.views
    foreign_keys = schema_analyzer.foreign_keys
    many_to_many_tables = schema_analyzer.many_to_many_tables

    # Get table order and circular dependencies
    ordered_tables, circular_tables = schema_analyzer.get_table_insertion_order()

    print("\n" + "=" * 80)
    print("DATABASE SCHEMA ANALYSIS REPORT")
    print("=" * 80)

    # Basic statistics
    print(f"\n1. BASIC STATISTICS")
    print(f"   Total tables: {len(tables)}")
    print(f"   Total views: {len(views)}")
    print(f"   Tables with foreign keys: {len(foreign_keys)}")
    print(f"   Many-to-many relationship tables: {len(many_to_many_tables)}")
    print(f"   Tables in circular dependencies: {len(circular_tables)}")

    # Table categories
    standalone_tables = [t for t in tables if t not in foreign_keys and t not in circular_tables]
    dependent_tables = [t for t in tables if t in foreign_keys and t not in circular_tables and t not in many_to_many_tables]

    print(f"\n2. TABLE CATEGORIES")
    print(f"   Standalone tables (no foreign keys): {len(standalone_tables)}")
    print(f"   Dependent tables (with foreign keys, no circular deps): {len(dependent_tables)}")
    print(f"   Many-to-many tables: {len(many_to_many_tables)}")
    print(f"   Tables in circular dependencies: {len(circular_tables)}")

    # Circular dependencies
    if circular_tables:
        # Separate mandatory and optional circular tables
        mandatory_circular_tables = set()
        optional_circular_tables = set()

        # Identify mandatory and optional circular tables
        for table in circular_tables:
            has_mandatory_circular_ref = False

            if table in foreign_keys:
                for fk in foreign_keys[table]:
                    if fk['referenced_table'] in circular_tables and not fk.get('is_nullable', True):
                        has_mandatory_circular_ref = True
                        break

            if has_mandatory_circular_ref:
                mandatory_circular_tables.add(table)
            else:
                optional_circular_tables.add(table)

        print(f"\n3. CIRCULAR DEPENDENCIES")
        print(f"   Total tables involved: {len(circular_tables)}")
        print(f"   Tables with mandatory (NOT NULL) circular references: {len(mandatory_circular_tables)}")
        print(f"   Tables with only optional (nullable) circular references: {len(optional_circular_tables)}")

        if mandatory_circular_tables:
            print(f"\n   Tables with mandatory circular references:")
            print(f"   {', '.join(sorted(mandatory_circular_tables))}")

        if optional_circular_tables:
            print(f"\n   Tables with only optional circular references:")
            print(f"   {', '.join(sorted(optional_circular_tables))}")

        # Find and print cycles
        # First, get all cycles from the dependency graph
        try:
            all_cycles = list(nx.simple_cycles(schema_analyzer.dependency_graph))

            # Classify cycles as mandatory or optional
            mandatory_cycles = []
            optional_cycles = []

            for cycle in all_cycles:
                # Check if all edges in the cycle are mandatory
                is_mandatory_cycle = True

                for i in range(len(cycle)):
                    from_node = cycle[i]
                    to_node = cycle[(i + 1) % len(cycle)]

                    # Find the corresponding foreign key
                    is_nullable = True  # Default to nullable
                    for fk in foreign_keys.get(from_node, []):
                        if fk['referenced_table'] == to_node:
                            is_nullable = fk.get('is_nullable', True)
                            break

                    if is_nullable:
                        is_mandatory_cycle = False
                        break

                if is_mandatory_cycle:
                    mandatory_cycles.append(cycle)
                else:
                    optional_cycles.append(cycle)

            # Print mandatory cycles
            if mandatory_cycles:
                print(f"\n   Mandatory circular dependencies (all NOT NULL FKs):")
                for i, cycle in enumerate(mandatory_cycles):
                    print(f"     Cycle {i+1}: {' -> '.join(cycle)} -> {cycle[0]}")

            # Print optional cycles
            if optional_cycles:
                print(f"\n   Optional circular dependencies (contain nullable FKs):")
                for i, cycle in enumerate(optional_cycles):
                    print(f"     Cycle {i+1}: {' -> '.join(cycle)} -> {cycle[0]}")
        except Exception as e:
            print(f"   Error detecting cycles: {e}")

        # Print foreign key relationships in circular dependencies
        print("\n   Foreign key relationships in circular dependencies:")
        for table in sorted(circular_tables):
            if table in foreign_keys:
                circular_fks = [fk for fk in foreign_keys[table] if fk['referenced_table'] in circular_tables]
                if circular_fks:
                    print(f"   - {table} references:")
                    for fk in circular_fks:
                        nullable_status = "NULL" if fk.get('is_nullable', True) else "NOT NULL"
                        print(f"     * {fk['column']} ({nullable_status}) -> {fk['referenced_table']}.{fk['referenced_column']}")

    # Many-to-many tables
    if many_to_many_tables:
        print(f"\n4. MANY-TO-MANY RELATIONSHIP TABLES")
        print(f"   Total detected: {len(many_to_many_tables)}")

        # Group by referenced tables for better organization
        references_to_tables = {}
        for table in sorted(many_to_many_tables):
            referenced_tables = sorted(set([fk['referenced_table'] for fk in foreign_keys[table]]))
            key = ' <-> '.join(referenced_tables)
            if key not in references_to_tables:
                references_to_tables[key] = []
            references_to_tables[key].append(table)

        # Print tables grouped by their references
        for i, (refs, tables) in enumerate(sorted(references_to_tables.items())):
            print(f"\n   Group {i+1}: Tables linking {refs}")
            for table in sorted(tables):
                # Get table details
                all_columns = {col['column_name'] for col in schema_analyzer.table_columns[table]}
                fk_columns = {fk['column'] for fk in foreign_keys[table]}
                pk_columns = {col['column_name'] for col in schema_analyzer.table_columns[table]
                             if col['column_key'] == 'PRI'}

                # Get unique referenced tables
                unique_referenced_tables = sorted(set([fk['referenced_table'] for fk in foreign_keys[table]]))

                print(f"     - {table}:")
                print(f"       * Links tables: {', '.join(unique_referenced_tables)}")
                print(f"       * Structure: {len(all_columns)} total columns, {len(fk_columns)} FK columns, {len(pk_columns)} PK columns")
                print(f"       * Foreign keys:")
                for fk in foreign_keys[table]:
                    print(f"         - {fk['column']} -> {fk['referenced_table']}.{fk['referenced_column']}")

                # Show non-FK columns
                non_fk_columns = all_columns - fk_columns
                if non_fk_columns:
                    print(f"       * Additional columns: {', '.join(sorted(non_fk_columns))}")

    # Table insertion order
    print(f"\n5. RECOMMENDED TABLE INSERTION ORDER")
    # Group tables for better readability
    standalone_in_order = [t for t in ordered_tables if t in standalone_tables]
    dependent_in_order = [t for t in ordered_tables if t in dependent_tables]
    circular_in_order = [t for t in ordered_tables if t in circular_tables]
    many_to_many_in_order = [t for t in ordered_tables if t in many_to_many_tables]

    print(f"   1. Standalone tables ({len(standalone_in_order)}):")
    for i, table in enumerate(standalone_in_order):
        print(f"      {i+1:3d}. {table}")

    print(f"\n   2. Dependent tables ({len(dependent_in_order)}):")
    for i, table in enumerate(dependent_in_order):
        print(f"      {i+1:3d}. {table}")

    print(f"\n   3. Tables in circular dependencies ({len(circular_in_order)}):")
    for i, table in enumerate(circular_in_order):
        print(f"      {i+1:3d}. {table}")

    print(f"\n   4. Many-to-many tables ({len(many_to_many_in_order)}):")
    for i, table in enumerate(many_to_many_in_order):
        print(f"      {i+1:3d}. {table}")

    # Complete ordered list
    print(f"\n6. COMPLETE ORDERED LIST FOR POPULATION ({len(ordered_tables)} tables)")
    for i, table in enumerate(ordered_tables):
        category = ""
        if table in standalone_tables:
            category = "(Standalone)"
        elif table in dependent_tables:
            category = "(Dependent)"
        elif table in circular_tables:
            category = "(Circular)"
        elif table in many_to_many_tables:
            category = "(Many-to-Many)"

        print(f"   {i+1:3d}. {table} {category}")

    print("\n" + "=" * 80)

def validate_connection_params(host, user, password, database, port):
    """
    Validate database connection parameters

    Args:
        host (str): Database host
        user (str): Database user
        password (str): Database password
        database (str): Database name
        port (str): Database port

    Returns:
        bool: True if all parameters are valid
    """
    if not host:
        logging.error("Database host is required")
        return False

    if not user:
        logging.error("Database user is required")
        return False

    if password is None:  # Empty password is allowed
        logging.warning("Database password is empty")

    if not database:
        logging.error("Database name is required")
        return False

    try:
        int(port)
    except ValueError:
        logging.error(f"Invalid port number: {port}")
        return False

    return True

def verify_table_population(db_connector, tables, min_records=1):
    """
    Verify that all tables have at least the minimum number of records

    Args:
        db_connector (DatabaseConnector): Database connector instance
        tables (list): List of tables to verify
        min_records (int, optional): Minimum number of records each table should have

    Returns:
        tuple: (success, empty_tables, partially_populated_tables)
            - success (bool): True if all tables have at least min_records
            - empty_tables (list): List of tables with zero records
            - partially_populated_tables (dict): Dict of tables with fewer than expected records
    """
    logging.info(f"Verifying that all tables have at least {min_records} record(s)...")

    empty_tables = []
    partially_populated_tables = {}

    for table in tables:
        query = f"SELECT COUNT(*) as count FROM {table}"
        result = db_connector.execute_query(query)

        if not result:
            logging.warning(f"Could not verify record count for table: {table}")
            empty_tables.append(table)
            continue

        count = result[0]['count']

        if count == 0:
            logging.warning(f"Table {table} has no records")
            empty_tables.append(table)
        elif count < min_records:
            logging.warning(f"Table {table} has only {count}/{min_records} expected records")
            partially_populated_tables[table] = count

    success = len(empty_tables) == 0 and len(partially_populated_tables) == 0

    if success:
        logging.info("Verification successful: All tables have at least the minimum number of records")
    else:
        if empty_tables:
            logging.error(f"Verification failed: {len(empty_tables)} tables have no records")
        if partially_populated_tables:
            logging.error(f"Verification failed: {len(partially_populated_tables)} tables are partially populated")

    return success, empty_tables, partially_populated_tables

def print_verification_results(empty_tables, partially_populated_tables, min_records):
    """
    Print the results of the table population verification

    Args:
        empty_tables (list): List of tables with zero records
        partially_populated_tables (dict): Dict of tables with fewer than expected records
        min_records (int): Minimum number of records each table should have
    """
    print("\n" + "=" * 50)
    print("TABLE POPULATION VERIFICATION RESULTS")
    print("=" * 50)

    if not empty_tables and not partially_populated_tables:
        print(f"✅ All tables have at least {min_records} record(s)")
        print("=" * 50)
        return

    if empty_tables:
        print(f"❌ {len(empty_tables)} tables have no records:")
        for table in sorted(empty_tables):
            print(f"  - {table}")
        print()

    if partially_populated_tables:
        print(f"⚠️  {len(partially_populated_tables)} tables are partially populated:")
        for table, count in sorted(partially_populated_tables.items()):
            print(f"  - {table}: {count}/{min_records} records")
        print()

    print("=" * 50)
