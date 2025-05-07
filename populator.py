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

        # Special handling for SyncSource and SyncSource_LogAlert
        # Make sure SyncSource is populated first
        if 'SyncSource' in ordered_tables and 'SyncSource_LogAlert' in ordered_tables:
            logging.info("Special handling for SyncSource and SyncSource_LogAlert tables")

            # Remove these tables from the ordered list
            ordered_tables = [t for t in ordered_tables if t not in ['SyncSource', 'SyncSource_LogAlert']]

            # Add SyncSource to the beginning of the list
            ordered_tables = ['SyncSource'] + ordered_tables

            # Add SyncSource_LogAlert to the end of the list
            ordered_tables.append('SyncSource_LogAlert')

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
        column_names = [col['column_name'] for col in columns]

        # Special handling for SyncSource table which has a column named 'Lag' (MySQL reserved keyword)
        if table == 'SyncSource':
            logging.info("Special handling for SyncSource table with reserved keyword columns")
            # Escape column names with backticks to handle reserved keywords
            escaped_column_names = [f"`{col_name}`" for col_name in column_names]

            # Prepare placeholders for SQL query
            placeholders = ', '.join(['%s'] * len(column_names))

            # Build INSERT query with escaped column names
            insert_query = f"INSERT INTO `{table}` ({', '.join(escaped_column_names)}) VALUES ({placeholders})"

            logging.debug(f"Using escaped column names for SyncSource: {insert_query}")
        else:
            # Prepare placeholders for SQL query
            placeholders = ', '.join(['%s'] * len(column_names))

            # Build INSERT query
            insert_query = f"INSERT INTO {table} ({', '.join(column_names)}) VALUES ({placeholders})"

        # Generate and insert data
        successful_inserts = 0
        for i in range(self.num_records):
            try:
                # Generate row data
                row_data = self._generate_row_data(table, columns, handle_circular)

                # Execute insert
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

        # Special handling for SyncSource_LogAlert table which has a circular dependency with SyncSource
        if table == 'SyncSource_LogAlert':
            # First, check if we have any SyncSource records in the database
            query = "SELECT ID FROM SyncSource LIMIT 1"
            result = self.db.execute_query(query)

            if result and len(result) > 0:
                # We have SyncSource records, so we can use them
                logging.info("Found existing SyncSource records to use for SyncSource_LogAlert")

                # Get all SyncSource IDs
                query = "SELECT ID FROM SyncSource"
                result = self.db.execute_query(query)

                if result and len(result) > 0:
                    # Store these IDs for use in the foreign key
                    sync_source_ids = [row['ID'] for row in result]

                    # Remember this for later when we process the SyncSource_ID column
                    self._sync_source_ids = sync_source_ids

        # Process columns
        for col in columns:
            column_name = col['column_name']

            # Special handling for SyncSource_LogAlert.SyncSource_ID
            if table == 'SyncSource_LogAlert' and column_name == 'SyncSource_ID' and hasattr(self, '_sync_source_ids') and self._sync_source_ids:
                # Use an existing SyncSource ID
                row_data[column_name] = random.choice(self._sync_source_ids)
                logging.info(f"Using existing SyncSource ID {row_data[column_name]} for SyncSource_LogAlert.SyncSource_ID")
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
                # Not a foreign key, generate a value based on column type
                row_data[column_name] = self.data_gen.generate_value(col, table_name=table)

        return row_data

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
        column_names = [col['column_name'] for col in columns]

        # Special handling for SyncSource table which has a column named 'Lag' (MySQL reserved keyword)
        if table == 'SyncSource':
            logging.info("Special handling for SyncSource table with reserved keyword columns")
            # Escape column names with backticks to handle reserved keywords
            escaped_column_names = [f"`{col_name}`" for col_name in column_names]

            # Prepare placeholders for SQL query
            placeholders = ', '.join(['%s'] * len(column_names))

            # Build INSERT query with escaped column names
            insert_query = f"INSERT INTO `{table}` ({', '.join(escaped_column_names)}) VALUES ({placeholders})"

            logging.debug(f"Using escaped column names for SyncSource: {insert_query}")
        else:
            # Prepare placeholders for SQL query
            placeholders = ', '.join(['%s'] * len(column_names))

            # Build INSERT query
            insert_query = f"INSERT INTO {table} ({', '.join(column_names)}) VALUES ({placeholders})"

        # Try multiple times with different random values
        for attempt in range(10):  # Try up to 10 times
            try:
                # Generate row data with special handling for circular dependencies
                row_data = self._generate_row_data(table, columns, handle_circular=True)

                # Execute insert
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
