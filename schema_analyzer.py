import logging
import networkx as nx
from collections import defaultdict

class SchemaAnalyzer:
    """
    Analyzes database schema, detects dependencies, and sorts tables for population
    """
    def __init__(self, db_connector):
        """
        Initialize with database connector

        Args:
            db_connector: DatabaseConnector instance
        """
        self.db = db_connector
        self.tables = []
        self.views = []
        self.foreign_keys = defaultdict(list)
        self.many_to_many_tables = set()
        self.table_columns = {}
        self.dependency_graph = nx.DiGraph()
        self.direct_circular_dependencies = []  # List of (parent_table, child_table) tuples for direct circular dependencies

    def analyze_schema(self):
        """
        Analyze database schema to extract tables, views, and foreign key relationships

        Returns:
            bool: Success status
        """
        try:
            # Get all tables (excluding views)
            tables_query = """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = %s
                AND table_type = 'BASE TABLE'
            """
            tables_result = self.db.execute_query(tables_query, (self.db.database,))

            if not tables_result:
                logging.error("Failed to retrieve tables from database")
                return False

            # Handle different case sensitivity in column names
            # Some MySQL configurations return 'TABLE_NAME' instead of 'table_name'
            try:
                # First try lowercase (standard)
                self.tables = [table['table_name'] for table in tables_result]
            except KeyError:
                try:
                    # Try uppercase
                    self.tables = [table['TABLE_NAME'] for table in tables_result]
                except KeyError:
                    # If both fail, log the keys that are available and return False
                    if tables_result and len(tables_result) > 0:
                        logging.error(f"Could not find table_name in result. Available keys: {list(tables_result[0].keys())}")
                    else:
                        logging.error("Empty result set when querying tables")
                    return False

            # Initialize check constraints dictionary
            self.check_constraints = {}

            # Get all views
            views_query = """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = %s
                AND table_type = 'VIEW'
            """
            views_result = self.db.execute_query(views_query, (self.db.database,))

            if views_result:
                try:
                    # First try lowercase (standard)
                    self.views = [view['table_name'] for view in views_result]
                except KeyError:
                    try:
                        # Try uppercase
                        self.views = [view['TABLE_NAME'] for view in views_result]
                    except KeyError:
                        # If both fail, log a warning but continue (views are optional)
                        if views_result and len(views_result) > 0:
                            logging.warning(f"Could not find table_name in views result. Available keys: {list(views_result[0].keys())}")
                        else:
                            logging.warning("Empty result set when querying views")
                        self.views = []

            # Get all columns for each table
            for table in self.tables:
                columns_query = """
                    SELECT
                        column_name,
                        data_type,
                        column_type,
                        character_maximum_length,
                        numeric_precision,
                        numeric_scale,
                        is_nullable,
                        column_key,
                        extra,
                        column_comment
                    FROM information_schema.columns
                    WHERE table_schema = %s
                    AND table_name = %s
                    ORDER BY ordinal_position
                """
                columns_result = self.db.execute_query(columns_query, (self.db.database, table))

                if not columns_result:
                    logging.warning(f"Failed to retrieve columns for table {table}")
                    continue

                # Check if we need to normalize column names for case sensitivity
                if columns_result and len(columns_result) > 0:
                    first_row = columns_result[0]
                    # If we have uppercase keys, normalize all rows
                    if 'COLUMN_NAME' in first_row and 'column_name' not in first_row:
                        normalized_results = []
                        for row in columns_result:
                            normalized_row = {
                                'column_name': row.get('COLUMN_NAME'),
                                'data_type': row.get('DATA_TYPE'),
                                'column_type': row.get('COLUMN_TYPE'),
                                'character_maximum_length': row.get('CHARACTER_MAXIMUM_LENGTH'),
                                'numeric_precision': row.get('NUMERIC_PRECISION'),
                                'numeric_scale': row.get('NUMERIC_SCALE'),
                                'is_nullable': row.get('IS_NULLABLE'),
                                'column_key': row.get('COLUMN_KEY'),
                                'extra': row.get('EXTRA'),
                                'column_comment': row.get('COLUMN_COMMENT')
                            }
                            normalized_results.append(normalized_row)
                        columns_result = normalized_results

                self.table_columns[table] = columns_result

            # Get all foreign keys
            fk_query = """
                SELECT
                    table_name,
                    column_name,
                    referenced_table_name,
                    referenced_column_name
                FROM information_schema.key_column_usage
                WHERE table_schema = %s
                AND referenced_table_name IS NOT NULL
                ORDER BY table_name, column_name
            """
            fk_result = self.db.execute_query(fk_query, (self.db.database,))

            if not fk_result:
                logging.info("No foreign keys found in the database")
            else:
                # Build foreign key relationships
                for fk in fk_result:
                    try:
                        # Try lowercase keys first (standard)
                        table_name = fk.get('table_name')
                        column_name = fk.get('column_name')
                        ref_table = fk.get('referenced_table_name')
                        ref_column = fk.get('referenced_column_name')

                        # If any key is missing, try uppercase
                        if None in (table_name, column_name, ref_table, ref_column):
                            table_name = fk.get('TABLE_NAME', table_name)
                            column_name = fk.get('COLUMN_NAME', column_name)
                            ref_table = fk.get('REFERENCED_TABLE_NAME', ref_table)
                            ref_column = fk.get('REFERENCED_COLUMN_NAME', ref_column)

                        # Skip if any key is still missing
                        if None in (table_name, column_name, ref_table, ref_column):
                            logging.warning(f"Skipping foreign key with missing data. Available keys: {list(fk.keys())}")
                            continue

                        # Determine if this foreign key is mandatory (NOT NULL)
                        is_nullable = True  # Default to nullable (optional)

                        # Find the column in table_columns to check if it's nullable
                        if table_name in self.table_columns:
                            for col in self.table_columns[table_name]:
                                if col['column_name'] == column_name:
                                    is_nullable = col['is_nullable'].upper() == 'YES'
                                    break

                        # Add foreign key with nullable information
                        self.foreign_keys[table_name].append({
                            'column': column_name,
                            'referenced_table': ref_table,
                            'referenced_column': ref_column,
                            'is_nullable': is_nullable
                        })

                        # Add edge to dependency graph with weight
                        # Use weight=1 for mandatory (NOT NULL) foreign keys
                        # Use weight=2 for optional (nullable) foreign keys
                        # This will make mandatory dependencies preferred in path finding
                        weight = 2 if is_nullable else 1
                        self.dependency_graph.add_edge(table_name, ref_table, weight=weight)
                    except Exception as e:
                        logging.warning(f"Error processing foreign key: {e}. Data: {fk}")
                        continue

            # Detect many-to-many relationship tables
            self._detect_many_to_many_tables()

            # Extract and analyze check constraints
            self._extract_check_constraints()

            return True

        except Exception as e:
            logging.error(f"Error analyzing schema: {e}")
            return False

    def _extract_check_constraints(self):
        """
        Extract and analyze check constraints from the database schema

        This method queries the database for check constraints and analyzes them
        to determine the valid ranges and conditions for columns.
        """
        try:
            # Query to get check constraints from MySQL 8.0+
            check_query = """
                SELECT
                    t.table_name,
                    c.constraint_name,
                    c.check_clause
                FROM
                    information_schema.check_constraints c
                JOIN
                    information_schema.table_constraints t
                ON
                    c.constraint_schema = t.constraint_schema
                    AND c.constraint_name = t.constraint_name
                WHERE
                    c.constraint_schema = %s
                ORDER BY
                    t.table_name, c.constraint_name
            """

            check_result = self.db.execute_query(check_query, (self.db.database,))

            if not check_result:
                logging.info("No check constraints found in the database")
                return

            # Process check constraints
            for constraint in check_result:
                try:
                    # Handle case sensitivity in column names
                    table_name = constraint.get('table_name', constraint.get('TABLE_NAME'))
                    constraint_name = constraint.get('constraint_name', constraint.get('CONSTRAINT_NAME'))
                    check_clause = constraint.get('check_clause', constraint.get('CHECK_CLAUSE'))

                    if not all([table_name, constraint_name, check_clause]):
                        logging.warning(f"Skipping check constraint with missing data. Available keys: {list(constraint.keys())}")
                        continue

                    # Initialize table entry if not exists
                    if table_name not in self.check_constraints:
                        self.check_constraints[table_name] = []

                    # Parse the check clause to extract column name and condition
                    logging.debug(f"Parsing check constraint '{constraint_name}' for table '{table_name}': {check_clause}")
                    parsed_constraint = self._parse_check_constraint(check_clause)

                    if parsed_constraint:
                        parsed_constraint['constraint_name'] = constraint_name
                        self.check_constraints[table_name].append(parsed_constraint)
                        logging.info(f"Extracted check constraint '{constraint_name}' for table '{table_name}': {parsed_constraint}")
                    else:
                        logging.warning(f"Could not parse check constraint '{constraint_name}' for table '{table_name}': {check_clause}")

                    # Always log the raw clause for debugging
                    logging.debug(f"Raw check clause for '{constraint_name}': {check_clause}")

                except Exception as e:
                    logging.warning(f"Error processing check constraint: {e}. Data: {constraint}")
                    continue

            # Log summary
            total_constraints = sum(len(constraints) for constraints in self.check_constraints.values())
            logging.info(f"Extracted {total_constraints} check constraints from {len(self.check_constraints)} tables")

        except Exception as e:
            logging.error(f"Error extracting check constraints: {e}")

    def _parse_check_constraint(self, check_clause):
        """
        Parse a check constraint clause to extract column name and condition

        Args:
            check_clause (str): The check constraint clause

        Returns:
            dict: Parsed constraint with column name and condition details, or None if parsing failed
        """
        import re

        # Common patterns in check constraints
        # 1. Simple range check: column_name >= value AND column_name <= value
        # 2. Simple equality check: column_name = value
        # 3. Simple IN check: column_name IN (value1, value2, ...)
        # 4. Simple BETWEEN check: column_name BETWEEN value1 AND value2

        # Initialize result
        result = {
            'raw_clause': check_clause,
            'type': 'unknown',
            'column': None,
            'min_value': None,
            'max_value': None,
            'allowed_values': None
        }

        # Clean up the check clause
        clean_clause = check_clause.strip().replace('`', '')

        # Try to extract column name
        column_match = re.search(r'^\(([a-zA-Z0-9_]+)', clean_clause)
        if column_match:
            result['column'] = column_match.group(1)

        # Check for range constraints (>= AND <=) with various formats
        # Format 1: (column >= value AND column <= value)
        range_match = re.search(r'\(([a-zA-Z0-9_]+)\s*>=\s*(-?\d+\.?\d*)\s*AND\s*([a-zA-Z0-9_]+)\s*<=\s*(-?\d+\.?\d*)\)', clean_clause)
        if range_match and range_match.group(1) == range_match.group(3):  # Same column in both conditions
            result['type'] = 'range'
            result['column'] = range_match.group(1)
            result['min_value'] = float(range_match.group(2))
            result['max_value'] = float(range_match.group(4))
            logging.debug(f"Parsed range constraint (format 1): {result['column']} between {result['min_value']} and {result['max_value']}")
            return result

        # Format 2: ((column >= value) and (column <= value))
        range_match2 = re.search(r'\(\(([a-zA-Z0-9_]+)\s*>=\s*(-?\d+\.?\d*)\)\s*and\s*\(([a-zA-Z0-9_]+)\s*<=\s*(-?\d+\.?\d*)\)\)', clean_clause, re.IGNORECASE)
        if range_match2 and range_match2.group(1) == range_match2.group(3):  # Same column in both conditions
            result['type'] = 'range'
            result['column'] = range_match2.group(1)
            result['min_value'] = float(range_match2.group(2))
            result['max_value'] = float(range_match2.group(4))
            logging.debug(f"Parsed range constraint (format 2): {result['column']} between {result['min_value']} and {result['max_value']}")
            return result

        # Check for BETWEEN constraints
        between_match = re.search(r'\(([a-zA-Z0-9_]+)\s+BETWEEN\s+(-?\d+\.?\d*)\s+AND\s+(-?\d+\.?\d*)\)', clean_clause)
        if between_match:
            result['type'] = 'between'
            result['column'] = between_match.group(1)
            result['min_value'] = float(between_match.group(2))
            result['max_value'] = float(between_match.group(3))
            return result

        # Check for IN constraints
        in_match = re.search(r'\(([a-zA-Z0-9_]+)\s+IN\s+\(([^)]+)\)\)', clean_clause)
        if in_match:
            result['type'] = 'in'
            result['column'] = in_match.group(1)
            # Parse the values in the IN clause
            values_str = in_match.group(2)
            values = [v.strip() for v in values_str.split(',')]
            # Try to convert to appropriate types
            try:
                # Try as integers first
                result['allowed_values'] = [int(v) for v in values]
            except ValueError:
                try:
                    # Try as floats
                    result['allowed_values'] = [float(v) for v in values]
                except ValueError:
                    # Keep as strings, removing quotes
                    result['allowed_values'] = [v.strip("'\"") for v in values]
            return result

        # Check for equality constraints
        eq_match = re.search(r'\(([a-zA-Z0-9_]+)\s*=\s*([^)]+)\)', clean_clause)
        if eq_match:
            result['type'] = 'equality'
            result['column'] = eq_match.group(1)
            value = eq_match.group(2).strip("'\"")
            # Try to convert to appropriate type
            try:
                # Try as integer
                result['allowed_values'] = [int(value)]
            except ValueError:
                try:
                    # Try as float
                    result['allowed_values'] = [float(value)]
                except ValueError:
                    # Keep as string
                    result['allowed_values'] = [value]
            return result

        # Enhanced BETWEEN pattern to handle more variations
        enhanced_between_match = re.search(r'\(([a-zA-Z0-9_]+)\s+BETWEEN\s+(\d+\.?\d*)\s+AND\s+(\d+\.?\d*)\)', clean_clause, re.IGNORECASE)
        if enhanced_between_match:
            result['type'] = 'between'
            result['column'] = enhanced_between_match.group(1)
            result['min_value'] = float(enhanced_between_match.group(2))
            result['max_value'] = float(enhanced_between_match.group(3))
            return result

        # Try to extract range constraints from raw clause as a last resort
        # This is a more generic approach for constraints that don't match the specific patterns above
        if result['type'] == 'unknown':
            # Look for patterns like (column >= min) and (column <= max)
            min_match = re.search(r'([a-zA-Z0-9_]+)\s*>=\s*(-?\d+\.?\d*)', clean_clause, re.IGNORECASE)
            max_match = re.search(r'([a-zA-Z0-9_]+)\s*<=\s*(-?\d+\.?\d*)', clean_clause, re.IGNORECASE)

            if min_match and max_match and min_match.group(1) == max_match.group(1):
                result['type'] = 'range'
                result['column'] = min_match.group(1)
                result['min_value'] = float(min_match.group(2))
                result['max_value'] = float(max_match.group(2))
                logging.debug(f"Parsed range constraint (generic format): {result['column']} between {result['min_value']} and {result['max_value']}")
                return result

            # Look for patterns like (column > min) and (column < max)
            min_match = re.search(r'([a-zA-Z0-9_]+)\s*>\s*(-?\d+\.?\d*)', clean_clause, re.IGNORECASE)
            max_match = re.search(r'([a-zA-Z0-9_]+)\s*<\s*(-?\d+\.?\d*)', clean_clause, re.IGNORECASE)

            if min_match and max_match and min_match.group(1) == max_match.group(1):
                result['type'] = 'range'
                result['column'] = min_match.group(1)
                result['min_value'] = float(min_match.group(2))
                result['max_value'] = float(max_match.group(2))
                logging.debug(f"Parsed range constraint (generic format): {result['column']} between {result['min_value']} and {result['max_value']}")
                return result

            # Handle single-sided constraints like (column >= min) or (column <= max)
            # First check for >= constraints
            min_match = re.search(r'\(([a-zA-Z0-9_]+)\s*>=\s*(-?\d+\.?\d*)\)', clean_clause, re.IGNORECASE)
            if min_match:
                result['type'] = 'range'
                result['column'] = min_match.group(1)
                result['min_value'] = float(min_match.group(2))
                # No max value specified, so leave it as None
                logging.debug(f"Parsed single-sided range constraint: {result['column']} >= {result['min_value']}")
                return result

            # Then check for <= constraints
            max_match = re.search(r'\(([a-zA-Z0-9_]+)\s*<=\s*(-?\d+\.?\d*)\)', clean_clause, re.IGNORECASE)
            if max_match:
                result['type'] = 'range'
                result['column'] = max_match.group(1)
                # No min value specified, so leave it as None
                result['max_value'] = float(max_match.group(2))
                logging.debug(f"Parsed single-sided range constraint: {result['column']} <= {result['max_value']}")
                return result

            # Check for > constraints
            min_match = re.search(r'\(([a-zA-Z0-9_]+)\s*>\s*(-?\d+\.?\d*)\)', clean_clause, re.IGNORECASE)
            if min_match:
                result['type'] = 'range'
                result['column'] = min_match.group(1)
                result['min_value'] = float(min_match.group(2))
                # Add a small epsilon to the min value since it's strictly greater than
                result['min_value'] += 0.000001 if '.' in min_match.group(2) else 1
                logging.debug(f"Parsed single-sided range constraint: {result['column']} > {min_match.group(2)}, adjusted to >= {result['min_value']}")
                return result

            # Check for < constraints
            max_match = re.search(r'\(([a-zA-Z0-9_]+)\s*<\s*(-?\d+\.?\d*)\)', clean_clause, re.IGNORECASE)
            if max_match:
                result['type'] = 'range'
                result['column'] = max_match.group(1)
                result['max_value'] = float(max_match.group(2))
                # Subtract a small epsilon from the max value since it's strictly less than
                result['max_value'] -= 0.000001 if '.' in max_match.group(2) else 1
                logging.debug(f"Parsed single-sided range constraint: {result['column']} < {max_match.group(2)}, adjusted to <= {result['max_value']}")
                return result

        # If we couldn't parse it, return the raw clause for manual handling
        logging.debug(f"Could not parse constraint into a specific type: {check_clause}")
        return result

    def _detect_many_to_many_tables(self):
        """
        Detect tables that represent many-to-many relationships

        This method uses multiple heuristics to identify many-to-many relationship tables:
        1. Table naming patterns (contains 'has', 'rel', 'map', etc.)
        2. Structure-based detection (foreign keys, primary keys)
        3. Reference patterns (tables that connect two other tables)
        """
        # Common naming patterns for many-to-many tables
        name_patterns = ['_has_', '_rel_', '_map_', '_mapping_', '_mm_', '_link_', '_to_', '_x_', '_2_']

        for table in self.tables:
            is_many_to_many = False
            reason = ""

            # Skip tables without at least 2 foreign keys
            if table not in self.foreign_keys or len(self.foreign_keys[table]) < 2:
                continue

            # Get foreign key columns and all columns
            fk_columns = {fk['column'] for fk in self.foreign_keys[table]}
            all_columns = {col['column_name'] for col in self.table_columns[table]}

            # Get primary key columns
            pk_columns = {col['column_name'] for col in self.table_columns[table]
                         if col['column_key'] == 'PRI'}

            # Get unique key columns (including primary keys)
            unique_columns = {col['column_name'] for col in self.table_columns[table]
                             if col['column_key'] in ('PRI', 'UNI')}

            # Get auto-increment columns
            auto_increment_columns = {col['column_name'] for col in self.table_columns[table]
                                     if col['extra'] and 'auto_increment' in col['extra'].lower()}

            # We'll get referenced tables when needed in each heuristic

            # HEURISTIC 1: Name-based detection
            table_lower = table.lower()
            for pattern in name_patterns:
                if pattern in table_lower:
                    is_many_to_many = True
                    reason = f"Name pattern match: '{pattern}'"
                    break

            # HEURISTIC 2: Structure-based detection - Classic pattern
            # A classic many-to-many table has:
            # - At least 2 foreign keys
            # - Primary key composed of those foreign keys
            # - Few or no other columns
            if not is_many_to_many:
                non_fk_columns = len(all_columns) - len(fk_columns)
                if (len(fk_columns) >= 2 and non_fk_columns <= 3 and
                    pk_columns and pk_columns.issubset(fk_columns)):
                    is_many_to_many = True
                    reason = "Classic pattern: PK composed of FKs, few other columns"

            # HEURISTIC 3: Structure-based detection - Modified pattern
            # A modified many-to-many table might have:
            # - At least 2 foreign keys
            # - Its own primary key (often auto-increment)
            # - Unique constraint on the combination of foreign keys
            # - Few other columns (timestamps, flags, etc.)
            if not is_many_to_many:
                non_fk_columns = len(all_columns) - len(fk_columns)
                if (len(fk_columns) >= 2 and non_fk_columns <= 5 and
                    len(auto_increment_columns) == 1 and auto_increment_columns.issubset(pk_columns)):
                    # Check if there's a unique constraint on foreign keys
                    if any(unique_columns.intersection(fk_columns)):
                        is_many_to_many = True
                        reason = "Modified pattern: Own PK, unique constraint on FKs"

            # HEURISTIC 4: Reference pattern
            # If a table references exactly 2 other tables and has few other columns
            if not is_many_to_many:
                # Get unique referenced tables
                unique_referenced_tables = set([fk['referenced_table'] for fk in self.foreign_keys[table]])
                non_fk_columns = len(all_columns) - len(fk_columns)
                if len(unique_referenced_tables) == 2 and non_fk_columns <= 5:
                    is_many_to_many = True
                    reason = "Reference pattern: Links exactly 2 tables with few other columns"

            # HEURISTIC 5: Composite foreign keys
            # If most columns are foreign keys and they reference different tables
            if not is_many_to_many:
                # Get unique referenced tables
                unique_referenced_tables = set([fk['referenced_table'] for fk in self.foreign_keys[table]])
                fk_ratio = len(fk_columns) / len(all_columns) if all_columns else 0
                if len(unique_referenced_tables) >= 2 and fk_ratio >= 0.5:
                    is_many_to_many = True
                    reason = f"Composite FKs: {len(fk_columns)}/{len(all_columns)} columns are FKs to {len(unique_referenced_tables)} tables"

            # Add to many-to-many tables if detected
            if is_many_to_many:
                self.many_to_many_tables.add(table)

                # Get the referenced tables for more detailed logging
                # Use a set to ensure unique referenced tables
                unique_referenced_tables_list = sorted(set([fk['referenced_table'] for fk in self.foreign_keys[table]]))
                fk_info = ', '.join([f"{fk['column']} -> {fk['referenced_table']}.{fk['referenced_column']}"
                                    for fk in self.foreign_keys[table]])

                logging.info(f"Detected many-to-many relationship table: {table}")
                logging.info(f"  - Detection reason: {reason}")
                logging.info(f"  - Links tables: {', '.join(unique_referenced_tables_list)}")
                logging.info(f"  - Foreign keys: {fk_info}")
                logging.info(f"  - Total columns: {len(all_columns)}, FK columns: {len(fk_columns)}, PK columns: {len(pk_columns)}")

    def get_table_insertion_order(self):
        """
        Determine the order in which tables should be populated

        Returns:
            list: Ordered list of tables for population
            set: Tables involved in circular dependencies
        """
        # First, analyze circular dependencies for logging purposes
        self._analyze_and_log_circular_dependencies()

        # Now, implement a proper table ordering algorithm that ensures:
        # 1. Tables without foreign keys come first
        # 2. Tables are ordered based on their dependencies
        # 3. Circular dependencies are handled properly

        # Start with an empty ordered list
        ordered_tables = []

        # Track tables that have been added to the ordered list
        included_tables = set()

        # Track tables involved in circular dependencies
        circular_tables = self._get_circular_tables()

        # Step 1: First add all tables without foreign keys (standalone tables)
        standalone_tables = [table for table in self.tables if table not in self.foreign_keys]
        for table in standalone_tables:
            ordered_tables.append(table)
            included_tables.add(table)

        logging.info(f"Added {len(standalone_tables)} standalone tables (no foreign keys) to the beginning of the order")

        # Step 2: Iteratively add tables whose dependencies are all satisfied
        progress = True
        iteration = 1

        while progress:
            progress = False
            tables_added_in_iteration = []

            # Find tables that can be added in this iteration
            for table in self.tables:
                # Skip tables that are already included
                if table in included_tables:
                    continue

                # Skip tables without foreign keys (already added)
                if table not in self.foreign_keys:
                    continue

                # Check if all referenced tables are already included
                all_dependencies_satisfied = True
                unsatisfied_dependencies = []

                for fk in self.foreign_keys[table]:
                    referenced_table = fk['referenced_table']
                    # If the foreign key is nullable, we can ignore this dependency
                    is_nullable = fk.get('is_nullable', False)

                    # If the referenced table is not yet included and the foreign key is NOT NULL
                    if referenced_table not in included_tables and not is_nullable:
                        all_dependencies_satisfied = False
                        unsatisfied_dependencies.append(f"{fk['column']} -> {referenced_table}.{fk['referenced_column']} (NOT NULL)")

                # If all dependencies are satisfied, add this table
                if all_dependencies_satisfied:
                    ordered_tables.append(table)
                    included_tables.add(table)
                    tables_added_in_iteration.append(table)
                    progress = True
                    logging.debug(f"Added table with satisfied dependencies: {table}")
                else:
                    logging.debug(f"Table {table} has unsatisfied dependencies: {', '.join(unsatisfied_dependencies)}")

            if tables_added_in_iteration:
                logging.info(f"Iteration {iteration}: Added {len(tables_added_in_iteration)} tables: {', '.join(tables_added_in_iteration)}")
            else:
                logging.info(f"Iteration {iteration}: No tables added")

            iteration += 1

        # Step 3: Handle remaining tables (those involved in circular dependencies)
        remaining_tables = [table for table in self.tables if table not in included_tables]

        if remaining_tables:
            logging.info(f"{len(remaining_tables)} tables remain with unsatisfied dependencies (likely circular)")

            # Create a subgraph of the remaining tables
            subgraph = self.dependency_graph.subgraph(remaining_tables).copy()

            # Break cycles in the subgraph
            self._break_cycles_in_graph(subgraph)

            # Get a topological sort of the subgraph
            try:
                remaining_ordered = list(nx.topological_sort(subgraph))
                logging.info(f"Successfully ordered remaining tables after breaking cycles")

                # Add the remaining tables to the ordered list
                for table in remaining_ordered:
                    if table not in included_tables:
                        ordered_tables.append(table)
                        included_tables.add(table)
            except nx.NetworkXUnfeasible:
                logging.error("Could not determine order for remaining tables even after breaking cycles")
                # Add remaining tables in arbitrary order as a fallback
                for table in remaining_tables:
                    if table not in included_tables:
                        ordered_tables.append(table)
                        included_tables.add(table)

        # Step 4: Move many-to-many tables to the end
        # First, remove them from their current positions
        many_to_many_in_order = [table for table in ordered_tables if table in self.many_to_many_tables]
        ordered_tables = [table for table in ordered_tables if table not in self.many_to_many_tables]

        # Then add them at the end
        ordered_tables.extend(many_to_many_in_order)

        if many_to_many_in_order:
            logging.info(f"Moved {len(many_to_many_in_order)} many-to-many tables to the end of the order")

        # Final check: ensure all tables are included
        if len(ordered_tables) != len(self.tables):
            missing_tables = set(self.tables) - set(ordered_tables)
            logging.warning(f"Some tables are missing from the ordered list: {', '.join(missing_tables)}")
            # Add any missing tables at the end
            for table in missing_tables:
                ordered_tables.append(table)

        # Log the final order
        logging.info(f"Final table insertion order determined: {len(ordered_tables)} tables")
        if logging.getLogger().level <= logging.DEBUG:
            for i, table in enumerate(ordered_tables):
                category = ""
                if table in standalone_tables:
                    category = "(Standalone)"
                elif table in self.many_to_many_tables:
                    category = "(Many-to-Many)"
                elif table in circular_tables:
                    category = "(Circular)"
                logging.debug(f"  {i+1}. {table} {category}")

        return ordered_tables, circular_tables

    def _analyze_and_log_circular_dependencies(self):
        """
        Analyze and log circular dependencies in the schema
        """
        logging.info("Analyzing circular dependencies in the schema...")

        # Find all cycles in the graph
        try:
            cycles = list(nx.simple_cycles(self.dependency_graph))
            logging.info(f"Found {len(cycles)} cycles in the dependency graph")
        except Exception as e:
            logging.error(f"Error detecting cycles: {e}")
            cycles = []

        # Classify cycles as mandatory or optional
        mandatory_cycles = []
        optional_cycles = []

        for cycle in cycles:
            # Check if all edges in the cycle are mandatory
            is_mandatory_cycle = True

            for i in range(len(cycle)):
                from_node = cycle[i]
                to_node = cycle[(i + 1) % len(cycle)]

                # Check if this edge represents an optional foreign key
                edge_data = self.dependency_graph.get_edge_data(from_node, to_node)
                if edge_data and edge_data.get('weight', 1) == 2:  # weight 2 = optional
                    is_mandatory_cycle = False
                    break

            if is_mandatory_cycle:
                mandatory_cycles.append(cycle)
            else:
                optional_cycles.append(cycle)

        # Create a more detailed log message about circular dependencies
        if cycles:
            # Log mandatory cycles
            if mandatory_cycles:
                cycle_details = []
                for i, cycle in enumerate(mandatory_cycles):
                    cycle_str = ' -> '.join(cycle)
                    cycle_details.append(f"Cycle {i+1}: {cycle_str}")

                if len(mandatory_cycles) == 1:
                    logging.info(f"Detected 1 mandatory circular dependency (all NOT NULL FKs): {cycle_details[0]}")
                else:
                    cycles_str = '\n  - '.join(cycle_details)
                    logging.info(f"Detected {len(mandatory_cycles)} mandatory circular dependencies (all NOT NULL FKs):\n  - {cycles_str}")

            # Log optional cycles
            if optional_cycles:
                cycle_details = []
                for i, cycle in enumerate(optional_cycles):
                    cycle_str = ' -> '.join(cycle)
                    cycle_details.append(f"Cycle {i+1}: {cycle_str}")

                if len(optional_cycles) == 1:
                    logging.info(f"Detected 1 optional circular dependency (contains nullable FKs): {cycle_details[0]}")
                else:
                    cycles_str = '\n  - '.join(cycle_details)
                    logging.info(f"Detected {len(optional_cycles)} optional circular dependencies (contain nullable FKs):\n  - {cycles_str}")

            # Log total
            total_msg = f"Total circular dependencies: {len(cycles)} ({len(mandatory_cycles)} mandatory, {len(optional_cycles)} optional)"
            logging.info(total_msg)

            # Identify direct circular dependencies (cycles of length 2)
            self.direct_circular_dependencies = []
            for cycle in cycles:
                if len(cycle) == 2:
                    # This is a direct circular dependency between two tables
                    parent_table, child_table = cycle
                    self.direct_circular_dependencies.append((parent_table, child_table))
                    logging.info(f"Detected direct circular dependency between {parent_table} and {child_table}")

            # Check for additional implicit circular dependencies that might not be detected as cycles
            # This happens when tables have foreign key relationships but aren't part of a cycle
            # in the dependency graph due to nullable foreign keys
            for table in self.tables:
                if table in self.foreign_keys:
                    for fk in self.foreign_keys[table]:
                        referenced_table = fk['referenced_table']
                        # Check if the referenced table also has foreign keys back to this table
                        if referenced_table in self.foreign_keys:
                            for ref_fk in self.foreign_keys[referenced_table]:
                                if ref_fk['referenced_table'] == table:
                                    # This is a potential circular dependency
                                    if (referenced_table, table) not in self.direct_circular_dependencies and \
                                       (table, referenced_table) not in self.direct_circular_dependencies:
                                        self.direct_circular_dependencies.append((referenced_table, table))
                                        logging.info(f"Detected implicit circular dependency: {referenced_table} -> {table}")
        else:
            logging.info("No circular dependencies detected in the schema")

        # Log tables involved in circular dependencies
        circular_tables = self._get_circular_tables()
        if circular_tables:
            # Get mandatory and optional circular tables
            mandatory_circular_tables, optional_circular_tables = self._get_circular_tables_by_type()

            # Log mandatory circular tables
            if mandatory_circular_tables:
                tables_list = ', '.join(sorted(mandatory_circular_tables))
                logging.info(f"Tables involved in mandatory circular dependencies: {tables_list}")

            # Log optional circular tables
            if optional_circular_tables:
                tables_list = ', '.join(sorted(optional_circular_tables))
                logging.info(f"Tables involved in optional circular dependencies: {tables_list}")

            # Log all circular tables
            tables_list = ', '.join(sorted(circular_tables))
            logging.info(f"All tables involved in circular dependencies: {tables_list}")

            # Log foreign key relationships between these tables for better understanding
            logging.info("Foreign key relationships in circular dependencies:")
            for table in circular_tables:
                if table in self.foreign_keys:
                    circular_fks = [fk for fk in self.foreign_keys[table]
                                   if fk['referenced_table'] in circular_tables]
                    if circular_fks:
                        for fk in circular_fks:
                            nullable_status = "NULL" if fk.get('is_nullable', True) else "NOT NULL"
                            logging.info(f"  - {table}.{fk['column']} ({nullable_status}) -> {fk['referenced_table']}.{fk['referenced_column']}")

    def _get_circular_tables(self):
        """
        Get all tables involved in circular dependencies

        Returns:
            set: Tables involved in circular dependencies
        """
        cycles = list(nx.simple_cycles(self.dependency_graph))
        circular_tables = set()

        for cycle in cycles:
            for table in cycle:
                circular_tables.add(table)

        return circular_tables

    def _get_circular_tables_by_type(self):
        """
        Get tables involved in circular dependencies, separated by type

        Returns:
            tuple: (mandatory_circular_tables, optional_circular_tables)
        """
        cycles = list(nx.simple_cycles(self.dependency_graph))
        mandatory_cycles = []
        optional_cycles = []

        for cycle in cycles:
            # Check if all edges in the cycle are mandatory
            is_mandatory_cycle = True

            for i in range(len(cycle)):
                from_node = cycle[i]
                to_node = cycle[(i + 1) % len(cycle)]

                # Check if this edge represents an optional foreign key
                edge_data = self.dependency_graph.get_edge_data(from_node, to_node)
                if edge_data and edge_data.get('weight', 1) == 2:  # weight 2 = optional
                    is_mandatory_cycle = False
                    break

            if is_mandatory_cycle:
                mandatory_cycles.append(cycle)
            else:
                optional_cycles.append(cycle)

        # Track tables involved in circular dependencies
        mandatory_circular_tables = set()
        optional_circular_tables = set()

        for cycle in mandatory_cycles:
            for table in cycle:
                mandatory_circular_tables.add(table)

        for cycle in optional_cycles:
            for table in cycle:
                if table not in mandatory_circular_tables:
                    optional_circular_tables.add(table)

        return mandatory_circular_tables, optional_circular_tables

    def _break_cycles_in_graph(self, graph):
        """
        Break cycles in a graph

        Args:
            graph: NetworkX graph to break cycles in
        """
        # Try to break cycles by removing edges from many-to-many tables first
        for table in self.many_to_many_tables:
            if table in graph:
                # Remove all outgoing edges from many-to-many tables
                edges_to_remove = list(graph.out_edges(table))
                graph.remove_edges_from(edges_to_remove)
                if edges_to_remove:
                    logging.info(f"Removed {len(edges_to_remove)} edges from many-to-many table {table}")

        # If cycles still exist, break them intelligently
        remaining_cycles = list(nx.simple_cycles(graph))

        # Classify remaining cycles
        remaining_mandatory_cycles = []
        remaining_optional_cycles = []

        for cycle in remaining_cycles:
            # Check if all edges in the cycle are mandatory
            is_mandatory_cycle = True

            for i in range(len(cycle)):
                from_node = cycle[i]
                to_node = cycle[(i + 1) % len(cycle)]

                # Check if this edge represents an optional foreign key
                edge_data = graph.get_edge_data(from_node, to_node)
                if edge_data and edge_data.get('weight', 1) == 2:  # weight 2 = optional
                    is_mandatory_cycle = False
                    break

            if is_mandatory_cycle:
                remaining_mandatory_cycles.append(cycle)
            else:
                remaining_optional_cycles.append(cycle)

        # Log remaining cycles
        if remaining_cycles:
            logging.info(f"After removing many-to-many edges, {len(remaining_cycles)} circular dependencies remain")
            logging.info(f"  - Mandatory cycles: {len(remaining_mandatory_cycles)}")
            logging.info(f"  - Optional cycles: {len(remaining_optional_cycles)}")

        # First break optional cycles by removing nullable foreign key edges
        for i, cycle in enumerate(remaining_optional_cycles):
            # Find the first nullable edge in the cycle
            nullable_edge = None

            for j in range(len(cycle)):
                from_node = cycle[j]
                to_node = cycle[(j + 1) % len(cycle)]

                # Check if this edge represents an optional foreign key
                edge_data = graph.get_edge_data(from_node, to_node)
                if edge_data and edge_data.get('weight', 1) == 2:  # weight 2 = optional
                    nullable_edge = (from_node, to_node)
                    break

            # Remove the nullable edge if found
            if nullable_edge:
                from_node, to_node = nullable_edge
                graph.remove_edge(from_node, to_node)
                logging.info(f"Breaking optional cycle {i+1} by removing nullable dependency: {from_node} -> {to_node}")

        # Then break any remaining mandatory cycles
        for i, cycle in enumerate(remaining_mandatory_cycles):
            # Make sure the cycle has at least 2 nodes
            if cycle and len(cycle) >= 2:
                # Remove one edge to break the cycle
                from_node, to_node = cycle[0], cycle[1]
                graph.remove_edge(from_node, to_node)
                logging.info(f"Breaking mandatory cycle {i+1} by removing NOT NULL dependency: {from_node} -> {to_node}")
            elif cycle and len(cycle) == 1:
                # Self-referencing node (rare but possible)
                node = cycle[0]
                logging.warning(f"Found self-referencing node in cycle {i+1}: {node}")
                if graph.has_edge(node, node):
                    graph.remove_edge(node, node)
                    logging.info(f"Breaking self-referencing cycle by removing dependency: {node} -> {node}")
            else:
                logging.warning(f"Found empty cycle {i+1}, skipping: {cycle}")

        # Check if there are still any cycles left (should be none)
        final_cycles = list(nx.simple_cycles(graph))
        if final_cycles:
            logging.warning(f"There are still {len(final_cycles)} unresolved cycles after breaking. This should not happen.")

            # Break any remaining cycles as a fallback
            for i, cycle in enumerate(final_cycles):
                if cycle and len(cycle) >= 2:
                    from_node, to_node = cycle[0], cycle[1]
                    graph.remove_edge(from_node, to_node)
                    logging.warning(f"Emergency breaking of cycle {i+1} by removing dependency: {from_node} -> {to_node}")
