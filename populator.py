import logging
import random
from collections import defaultdict
from mysql.connector import Error

class DatabasePopulator:
    """
    Populates database tables with fake data
    """
    def __init__(self, db_connector, schema_analyzer, data_generator, num_records=10, max_retries=5):
        """
        Initialize with database connector, schema analyzer, and data generator

        Args:
            db_connector: DatabaseConnector instance
            schema_analyzer: SchemaAnalyzer instance
            data_generator: DataGenerator instance
            num_records (int): Number of records to generate per table
            max_retries (int): Maximum number of retries for handling circular dependencies
        """
        self.db = db_connector
        self.schema = schema_analyzer
        self.data_gen = data_generator
        self.num_records = num_records
        self.max_retries = max_retries
        self.inserted_data = defaultdict(list)
        self.failed_tables = set()

    def populate_database(self):
        """
        Populate all tables in the database

        Returns:
            bool: Success status
        """
        # Analyze schema
        if not self.schema.analyze_schema():
            logging.error("Failed to analyze database schema")
            return False

        # Get table insertion order
        ordered_tables, circular_tables = self.schema.get_table_insertion_order()

        if not ordered_tables:
            logging.error("No tables to populate")
            return False

        logging.info(f"Tables will be populated in the following order: {', '.join(ordered_tables)}")
        logging.info(f"Tables involved in circular dependencies: {', '.join(circular_tables)}")

        # Handle tables with circular dependencies by ensuring proper order
        # For tables with direct circular dependencies, ensure the parent table is populated first
        for table_pair in self.schema.direct_circular_dependencies:
            parent_table, child_table = table_pair

            if parent_table in ordered_tables and child_table in ordered_tables:
                logging.info(f"Handling circular dependency between {parent_table} and {child_table}")

                # Remove these tables from the ordered list
                ordered_tables = [t for t in ordered_tables if t not in [parent_table, child_table]]

                # Add parent table first, then child table at the end
                ordered_tables = [parent_table] + ordered_tables
                ordered_tables.append(child_table)

        # First pass: populate tables without circular dependencies
        non_circular_tables = [table for table in ordered_tables if table not in circular_tables]
        for table in non_circular_tables:
            self._populate_table(table)

        # Second pass: populate tables with circular dependencies
        if circular_tables:
            logging.info("Starting second pass to populate tables with circular dependencies")

            # Try to populate each table in the circular dependency
            for table in [t for t in ordered_tables if t in circular_tables]:
                self._populate_table(table, handle_circular=True)

            # Check if any tables failed to populate
            if self.failed_tables:
                logging.warning(f"Some tables could not be fully populated: {', '.join(self.failed_tables)}")

                # Try random table order for failed tables
                self._handle_failed_tables()

        # Final check
        success = len(self.failed_tables) == 0
        if success:
            logging.info("All tables successfully populated")
        else:
            logging.warning(f"The following tables could not be fully populated: {', '.join(self.failed_tables)}")

        return success

    def _populate_table(self, table, handle_circular=False):
        """
        Populate a single table with fake data

        Args:
            table (str): Table name
            handle_circular (bool): Whether to handle circular dependencies

        Returns:
            bool: Success status
        """
        if table not in self.schema.table_columns:
            logging.error(f"Table {table} not found in schema")
            self.failed_tables.add(table)
            return False

        logging.info(f"Populating table: {table}")

        # Get column information
        columns = self.schema.table_columns[table]

        # Filter out generated columns
        non_generated_columns = []
        for col in columns:
            if 'generated' not in col.get('extra', '').lower():
                non_generated_columns.append(col)
            else:
                logging.info(f"Skipping generated column {table}.{col['column_name']} in INSERT statement")

        column_names = [col['column_name'] for col in non_generated_columns]

        # Always escape table and column names with backticks to handle reserved keywords
        escaped_column_names = [f"`{col_name}`" for col_name in column_names]

        # Check if any columns are spatial data types (POINT, POLYGON, LINESTRING)
        spatial_columns = []
        spatial_column_types = {}
        for col in non_generated_columns:
            data_type = col['data_type'].lower()
            if data_type in ('point', 'polygon', 'linestring'):
                spatial_columns.append(col['column_name'])
                spatial_column_types[col['column_name']] = data_type
                logging.info(f"Found spatial column {table}.{col['column_name']} of type {data_type}")

        # For spatial data, we need to use a different approach
        if spatial_columns:
            # Build a custom INSERT query with the ST_GeomFromText function for spatial columns
            value_parts = []
            for col_name in column_names:
                if col_name in spatial_columns:
                    # For spatial columns, use the ST_GeomFromText function directly in the SQL
                    value_parts.append(f"ST_GeomFromText(%s)")
                else:
                    # For non-spatial columns, use normal placeholders
                    value_parts.append('%s')

            # Build INSERT query with escaped table and column names
            insert_query = f"INSERT INTO `{table}` ({', '.join(escaped_column_names)}) VALUES ({', '.join(value_parts)})"
        else:
            # Standard INSERT query for non-spatial data
            placeholders = ', '.join(['%s'] * len(column_names))
            insert_query = f"INSERT INTO `{table}` ({', '.join(escaped_column_names)}) VALUES ({placeholders})"

        # Log if the table has reserved keyword columns
        mysql_reserved_keywords = ['ADD', 'ALL', 'ALTER', 'ANALYZE', 'AND', 'AS', 'ASC', 'ASENSITIVE',
                                  'BEFORE', 'BETWEEN', 'BIGINT', 'BINARY', 'BLOB', 'BOTH', 'BY',
                                  'CALL', 'CASCADE', 'CASE', 'CHANGE', 'CHAR', 'CHARACTER', 'CHECK',
                                  'COLLATE', 'COLUMN', 'CONDITION', 'CONSTRAINT', 'CONTINUE', 'CONVERT',
                                  'CREATE', 'CROSS', 'CURRENT_DATE', 'CURRENT_TIME', 'CURRENT_TIMESTAMP',
                                  'CURRENT_USER', 'CURSOR', 'DATABASE', 'DATABASES', 'DAY_HOUR',
                                  'DAY_MICROSECOND', 'DAY_MINUTE', 'DAY_SECOND', 'DEC', 'DECIMAL',
                                  'DECLARE', 'DEFAULT', 'DELAYED', 'DELETE', 'DESC', 'DESCRIBE',
                                  'DETERMINISTIC', 'DISTINCT', 'DISTINCTROW', 'DIV', 'DOUBLE', 'DROP',
                                  'DUAL', 'EACH', 'ELSE', 'ELSEIF', 'ENCLOSED', 'ESCAPED', 'EXISTS',
                                  'EXIT', 'EXPLAIN', 'FALSE', 'FETCH', 'FLOAT', 'FLOAT4', 'FLOAT8',
                                  'FOR', 'FORCE', 'FOREIGN', 'FROM', 'FULLTEXT', 'GRANT', 'GROUP',
                                  'HAVING', 'HIGH_PRIORITY', 'HOUR_MICROSECOND', 'HOUR_MINUTE',
                                  'HOUR_SECOND', 'IF', 'IGNORE', 'IN', 'INDEX', 'INFILE', 'INNER',
                                  'INOUT', 'INSENSITIVE', 'INSERT', 'INT', 'INT1', 'INT2', 'INT3',
                                  'INT4', 'INT8', 'INTEGER', 'INTERVAL', 'INTO', 'IS', 'ITERATE',
                                  'JOIN', 'KEY', 'KEYS', 'KILL', 'LEADING', 'LEAVE', 'LEFT', 'LIKE',
                                  'LIMIT', 'LINES', 'LOAD', 'LOCALTIME', 'LOCALTIMESTAMP', 'LOCK',
                                  'LONG', 'LONGBLOB', 'LONGTEXT', 'LOOP', 'LOW_PRIORITY', 'MATCH',
                                  'MEDIUMBLOB', 'MEDIUMINT', 'MEDIUMTEXT', 'MIDDLEINT', 'MINUTE_MICROSECOND',
                                  'MINUTE_SECOND', 'MOD', 'MODIFIES', 'NATURAL', 'NOT', 'NO_WRITE_TO_BINLOG',
                                  'NULL', 'NUMERIC', 'ON', 'OPTIMIZE', 'OPTION', 'OPTIONALLY', 'OR',
                                  'ORDER', 'OUT', 'OUTER', 'OUTFILE', 'PRECISION', 'PRIMARY', 'PROCEDURE',
                                  'PURGE', 'RANGE', 'READ', 'READS', 'READ_ONLY', 'READ_WRITE', 'REAL',
                                  'REFERENCES', 'REGEXP', 'RELEASE', 'RENAME', 'REPEAT', 'REPLACE',
                                  'REQUIRE', 'RESTRICT', 'RETURN', 'REVOKE', 'RIGHT', 'RLIKE', 'SCHEMA',
                                  'SCHEMAS', 'SECOND_MICROSECOND', 'SELECT', 'SENSITIVE', 'SEPARATOR',
                                  'SET', 'SHOW', 'SMALLINT', 'SPATIAL', 'SPECIFIC', 'SQL', 'SQLEXCEPTION',
                                  'SQLSTATE', 'SQLWARNING', 'SQL_BIG_RESULT', 'SQL_CALC_FOUND_ROWS',
                                  'SQL_SMALL_RESULT', 'SSL', 'STARTING', 'STRAIGHT_JOIN', 'TABLE',
                                  'TERMINATED', 'THEN', 'TINYBLOB', 'TINYINT', 'TINYTEXT', 'TO',
                                  'TRAILING', 'TRIGGER', 'TRUE', 'UNDO', 'UNION', 'UNIQUE', 'UNLOCK',
                                  'UNSIGNED', 'UPDATE', 'USAGE', 'USE', 'USING', 'UTC_DATE', 'UTC_TIME',
                                  'UTC_TIMESTAMP', 'VALUES', 'VARBINARY', 'VARCHAR', 'VARCHARACTER',
                                  'VARYING', 'WHEN', 'WHERE', 'WHILE', 'WITH', 'WRITE', 'X509',
                                  'XOR', 'YEAR_MONTH', 'ZEROFILL', 'LAG']

        reserved_keywords_in_columns = [col for col in column_names if col.upper() in mysql_reserved_keywords]
        if reserved_keywords_in_columns:
            logging.info(f"Table {table} has columns with MySQL reserved keywords: {', '.join(reserved_keywords_in_columns)}")

        # Generate and insert data
        successful_inserts = 0
        for i in range(self.num_records):
            try:
                # Generate row data
                row_data = self._generate_row_data(table, non_generated_columns, handle_circular)

                # For spatial data, we need to modify the query to use the values directly
                if spatial_columns:
                    # Create a modified query with the spatial data values directly in the SQL
                    modified_values = []
                    for col_name in column_names:
                        modified_values.append(row_data[col_name])

                    # Execute the modified query
                    if self.db.execute_query(insert_query, tuple(modified_values), commit=True):
                        # Get the inserted ID if there's an auto-increment column
                        last_id = None
                        for col in columns:
                            if col['extra'] == 'auto_increment':
                                last_id_query = "SELECT LAST_INSERT_ID() as id"
                                result = self.db.execute_query(last_id_query)
                                if result and result[0]['id']:
                                    last_id = result[0]['id']
                                    row_data[col['column_name']] = last_id

                        # Store inserted data for foreign key references
                        self.inserted_data[table].append(row_data)
                        successful_inserts += 1
                    else:
                        raise Error(f"Failed to insert data into {table}")
                else:
                    # Standard INSERT query for non-spatial data
                    if self.db.execute_query(insert_query, tuple(row_data.values()), commit=True):
                        # Get the inserted ID if there's an auto-increment column
                        last_id = None
                        for col in columns:
                            if col['extra'] == 'auto_increment':
                                last_id_query = "SELECT LAST_INSERT_ID() as id"
                                result = self.db.execute_query(last_id_query)
                                if result and result[0]['id']:
                                    last_id = result[0]['id']
                                    row_data[col['column_name']] = last_id

                        # Store inserted data for foreign key references
                        self.inserted_data[table].append(row_data)
                        successful_inserts += 1

            except Error as e:
                logging.error(f"Error inserting into {table}: {e}")
                # Continue with next record

        # Check if all records were inserted successfully
        if successful_inserts < self.num_records:
            logging.warning(f"Only {successful_inserts}/{self.num_records} records inserted into {table}")
            if successful_inserts == 0:
                self.failed_tables.add(table)
                return False

        return True

    def _generate_row_data(self, table, columns, handle_circular=False):
        """
        Generate data for a single row

        Args:
            table (str): Table name
            columns (list): List of column information dictionaries
            handle_circular (bool): Whether to handle circular dependencies

        Returns:
            dict: Generated row data
        """
        row_data = {}

        # Check if this table is part of a known circular dependency
        circular_deps = []
        for parent_table, child_table in getattr(self.schema, 'direct_circular_dependencies', []):
            if table == child_table:
                circular_deps.append((parent_table, child_table))

        # For tables with circular dependencies, pre-fetch parent table IDs
        for parent_table, _ in circular_deps:
            # Get the primary key column name for the parent table
            pk_column = self._get_primary_key_column(parent_table)
            if not pk_column:
                logging.warning(f"Could not determine primary key column for {parent_table}")
                continue

            # Check if we have any parent table records in the database
            query = f"SELECT `{pk_column}` FROM `{parent_table}` LIMIT 1"
            result = self.db.execute_query(query)

            if result and len(result) > 0:
                # We have parent table records, so we can use them
                logging.info(f"Found existing {parent_table} records to use for {table}")

                # Get all parent table IDs
                query = f"SELECT `{pk_column}` FROM `{parent_table}`"
                result = self.db.execute_query(query)

                if result and len(result) > 0:
                    # Store these IDs for use in the foreign key
                    parent_ids = [row[pk_column] for row in result]

                    # Remember this for later when we process the foreign key column
                    # Use a dictionary to store IDs for multiple parent tables
                    if not hasattr(self, '_parent_table_ids'):
                        self._parent_table_ids = {}
                    self._parent_table_ids[parent_table] = parent_ids

                    # Also store the primary key column name for reference
                    if not hasattr(self, '_parent_table_pk_columns'):
                        self._parent_table_pk_columns = {}
                    self._parent_table_pk_columns[parent_table] = pk_column

        # Process columns
        for col in columns:
            column_name = col['column_name']

            # Handle foreign keys for tables with circular dependencies
            if hasattr(self, '_parent_table_ids') and hasattr(self, '_parent_table_pk_columns'):
                # Check if this column is a foreign key to a parent table in a circular dependency
                for parent_table, parent_ids in self._parent_table_ids.items():
                    # Get the primary key column for this parent table
                    parent_pk_column = self._parent_table_pk_columns.get(parent_table)
                    if not parent_pk_column:
                        continue

                    # Check if this column references the parent table's primary key
                    if table in self.schema.foreign_keys:
                        for fk in self.schema.foreign_keys[table]:
                            if fk['column'] == column_name and fk['referenced_table'] == parent_table and fk['referenced_column'] == parent_pk_column:
                                # Use an existing parent table ID
                                row_data[column_name] = random.choice(parent_ids)
                                logging.info(f"Using existing {parent_table} {parent_pk_column} {row_data[column_name]} for {table}.{column_name}")
                                continue

            # Check if this is a foreign key
            is_foreign_key = False
            referenced_table = None
            referenced_column = None

            if table in self.schema.foreign_keys:
                for fk in self.schema.foreign_keys[table]:
                    if fk['column'] == column_name:
                        is_foreign_key = True
                        referenced_table = fk['referenced_table']
                        referenced_column = fk['referenced_column']
                        break

            # Handle foreign key
            if is_foreign_key:
                # Check if this foreign key is nullable
                is_nullable = col['is_nullable'].lower() == 'yes'

                # Find the corresponding foreign key entry to get additional info
                fk_info = None
                if table in self.schema.foreign_keys:
                    for fk in self.schema.foreign_keys[table]:
                        if fk['column'] == column_name and fk['referenced_table'] == referenced_table:
                            fk_info = fk
                            break

                # If we found the FK info, use its nullable status (which might be more accurate)
                if fk_info and 'is_nullable' in fk_info:
                    is_nullable = fk_info['is_nullable']

                # Check if referenced table has data
                if referenced_table in self.inserted_data and self.inserted_data[referenced_table]:
                    # Use an existing value from the referenced table
                    referenced_row = random.choice(self.inserted_data[referenced_table])
                    row_data[column_name] = referenced_row[referenced_column]
                elif is_nullable:
                    # This is a nullable foreign key, so we can set it to NULL
                    logging.info(f"Setting nullable foreign key {table}.{column_name} -> {referenced_table}.{referenced_column} to NULL")
                    row_data[column_name] = None
                elif handle_circular:
                    # This is a circular dependency with NOT NULL constraint
                    logging.warning(f"Circular dependency detected for {table}.{column_name} -> {referenced_table}.{referenced_column} (NOT NULL)")

                    # Try to find any value in the referenced table
                    query = f"SELECT {referenced_column} FROM {referenced_table} LIMIT 1"
                    result = self.db.execute_query(query)

                    if result and result[0][referenced_column] is not None:
                        # Use existing value from database
                        row_data[column_name] = result[0][referenced_column]
                        logging.info(f"Using existing value from database for {table}.{column_name} -> {referenced_table}.{referenced_column}")
                    else:
                        # No existing value, this is a hard circular dependency
                        # Generate a placeholder value that will be fixed later
                        placeholder = self._generate_placeholder_value(col)
                        row_data[column_name] = placeholder
                        logging.info(f"Generated placeholder value {placeholder} for {table}.{column_name} -> {referenced_table}.{referenced_column}")
                else:
                    # Referenced table not yet populated and not handling circular dependencies
                    # This should not happen if tables are properly ordered
                    logging.error(f"Referenced table {referenced_table} not yet populated for {table}.{column_name} (NOT NULL)")

                    # Generate a placeholder value
                    placeholder = self._generate_placeholder_value(col)
                    row_data[column_name] = placeholder
                    logging.info(f"Generated placeholder value {placeholder} for {table}.{column_name} -> {referenced_table}.{referenced_column}")
            else:
                # Check if this is a generated column (GENERATED ALWAYS AS)
                is_generated = 'generated' in col.get('extra', '').lower()

                if is_generated:
                    # Skip generating values for generated columns
                    logging.info(f"Skipping generated column {table}.{column_name}")
                    continue
                else:
                    # Not a foreign key or generated column, generate a value based on column type
                    # Pass the current row data to handle related fields
                    row_data[column_name] = self.data_gen.generate_value(col, table_name=table, current_record=row_data)

        return row_data

    def _get_primary_key_column(self, table_name):
        """
        Get the primary key column name for a table

        Args:
            table_name (str): Table name

        Returns:
            str: Primary key column name or None if not found
        """
        # Check if we have the table columns information
        if table_name not in self.schema.table_columns:
            logging.warning(f"No column information available for table {table_name}")
            return None

        # Look for the primary key column
        for col in self.schema.table_columns[table_name]:
            if col.get('column_key') == 'PRI':
                return col['column_name']

        # If no primary key found, look for an auto_increment column
        for col in self.schema.table_columns[table_name]:
            if 'auto_increment' in col.get('extra', ''):
                return col['column_name']

        # If still not found, return None
        logging.warning(f"Could not find primary key column for table {table_name}")
        return None

    def _generate_placeholder_value(self, column_info):
        """
        Generate a placeholder value for a column when handling circular dependencies

        Args:
            column_info (dict): Column information

        Returns:
            object: Generated placeholder value
        """
        # For primary keys, try to generate a unique value
        if column_info['column_key'] == 'PRI':
            data_type = column_info['data_type'].lower()

            if data_type in ('int', 'bigint', 'smallint', 'tinyint', 'mediumint'):
                # For integer primary keys, generate a large random number
                return random.randint(1000000, 9999999)
            elif data_type in ('varchar', 'char'):
                # For string primary keys, generate a UUID-like string
                return f"temp-{random.randint(100000, 999999)}"

        # For other columns, generate a normal value
        return self.data_gen.generate_value(column_info, table_name=None)

    def _handle_failed_tables(self):
        """
        Try to populate failed tables by trying random orders
        """
        logging.info("Attempting to resolve failed tables with random ordering")

        # Copy the failed tables set
        remaining_tables = self.failed_tables.copy()
        retry_count = 0

        while remaining_tables and retry_count < self.max_retries:
            retry_count += 1
            logging.info(f"Retry {retry_count}/{self.max_retries} for failed tables")

            # Try tables in random order
            tables_to_try = list(remaining_tables)
            random.shuffle(tables_to_try)

            # Track tables that were successfully populated in this iteration
            success_in_iteration = set()

            for table in tables_to_try:
                if self._populate_table(table, handle_circular=True):
                    success_in_iteration.add(table)

            # Remove successfully populated tables from the remaining set
            remaining_tables -= success_in_iteration

            # If no progress was made in this iteration, try a different approach
            if not success_in_iteration and remaining_tables:
                logging.info("No progress made in this iteration, trying partial population")

                # Try to insert at least one record in each remaining table
                for table in list(remaining_tables):
                    if self._try_partial_population(table):
                        remaining_tables.remove(table)

        # Update the failed tables set
        self.failed_tables = remaining_tables

    def _try_partial_population(self, table):
        """
        Try to populate a table with at least one record

        Args:
            table (str): Table name

        Returns:
            bool: Success status
        """
        logging.info(f"Attempting partial population of table: {table}")

        # Get column information
        columns = self.schema.table_columns[table]

        # Filter out generated columns
        non_generated_columns = []
        for col in columns:
            if 'generated' not in col.get('extra', '').lower():
                non_generated_columns.append(col)
            else:
                logging.info(f"Skipping generated column {table}.{col['column_name']} in partial population")

        column_names = [col['column_name'] for col in non_generated_columns]

        # Always escape table and column names with backticks to handle reserved keywords
        escaped_column_names = [f"`{col_name}`" for col_name in column_names]

        # Check if any columns are spatial data types (POINT, POLYGON, LINESTRING)
        spatial_columns = []
        spatial_column_types = {}
        for col in non_generated_columns:
            data_type = col['data_type'].lower()
            if data_type in ('point', 'polygon', 'linestring'):
                spatial_columns.append(col['column_name'])
                spatial_column_types[col['column_name']] = data_type
                logging.info(f"Found spatial column {table}.{col['column_name']} of type {data_type}")

        # For spatial data, we need to use a different approach
        if spatial_columns:
            # Build a custom INSERT query with the ST_GeomFromText function for spatial columns
            value_parts = []
            for col_name in column_names:
                if col_name in spatial_columns:
                    # For spatial columns, use the ST_GeomFromText function directly in the SQL
                    value_parts.append(f"ST_GeomFromText(%s)")
                else:
                    # For non-spatial columns, use normal placeholders
                    value_parts.append('%s')

            # Build INSERT query with escaped table and column names
            insert_query = f"INSERT INTO `{table}` ({', '.join(escaped_column_names)}) VALUES ({', '.join(value_parts)})"
        else:
            # Standard INSERT query for non-spatial data
            placeholders = ', '.join(['%s'] * len(column_names))
            insert_query = f"INSERT INTO `{table}` ({', '.join(escaped_column_names)}) VALUES ({placeholders})"

        # Try multiple times with different random values
        for attempt in range(10):  # Try up to 10 times
            try:
                # Generate row data with special handling for circular dependencies
                row_data = self._generate_row_data(table, non_generated_columns, handle_circular=True)

                # For spatial data, we need to modify the query to use the values directly
                if spatial_columns:
                    # Create a modified query with the spatial data values directly in the SQL
                    modified_values = []
                    for col_name in column_names:
                        modified_values.append(row_data[col_name])

                    # Execute the modified query
                    if self.db.execute_query(insert_query, tuple(modified_values), commit=True):
                        # Get the inserted ID if there's an auto-increment column
                        for col in columns:
                            if col['extra'] == 'auto_increment':
                                last_id_query = "SELECT LAST_INSERT_ID() as id"
                                result = self.db.execute_query(last_id_query)
                                if result and result[0]['id']:
                                    row_data[col['column_name']] = result[0]['id']

                        # Store inserted data for foreign key references
                        self.inserted_data[table].append(row_data)
                        logging.info(f"Successfully inserted one record into {table}")
                        return True
                    else:
                        raise Error(f"Failed to insert data into {table}")
                else:
                    # Standard INSERT query for non-spatial data
                    if self.db.execute_query(insert_query, tuple(row_data.values()), commit=True):
                        # Get the inserted ID if there's an auto-increment column
                        for col in columns:
                            if col['extra'] == 'auto_increment':
                                last_id_query = "SELECT LAST_INSERT_ID() as id"
                                result = self.db.execute_query(last_id_query)
                                if result and result[0]['id']:
                                    row_data[col['column_name']] = result[0]['id']

                        # Store inserted data for foreign key references
                        self.inserted_data[table].append(row_data)
                        logging.info(f"Successfully inserted one record into {table}")
                        return True

            except Error as e:
                logging.debug(f"Attempt {attempt+1} failed for {table}: {e}")
                # Continue with next attempt

        logging.error(f"Failed to insert even one record into {table} after multiple attempts")
        return False
