import re
import random
import logging
from datetime import datetime, timedelta
from faker import Faker
from decimal import Decimal

class DataGenerator:
    """
    Generates fake data based on column types and constraints
    """
    def __init__(self, locale='en_US', schema_analyzer=None):
        """
        Initialize with Faker instance

        Args:
            locale (str): Locale for Faker
            schema_analyzer (SchemaAnalyzer, optional): Schema analyzer instance for check constraints
        """
        self.faker = Faker(locale)
        self.schema_analyzer = schema_analyzer
        self._current_record = {}
        self.type_generators = {
            'varchar': self._generate_varchar,
            'char': self._generate_char,
            'text': self._generate_text,
            'tinytext': self._generate_tinytext,
            'mediumtext': self._generate_mediumtext,
            'longtext': self._generate_longtext,
            'int': self._generate_int,
            'tinyint': self._generate_tinyint,
            'smallint': self._generate_smallint,
            'mediumint': self._generate_mediumint,
            'bigint': self._generate_bigint,
            'float': self._generate_float,
            'double': self._generate_double,
            'decimal': self._generate_decimal,
            'date': self._generate_date,
            'datetime': self._generate_datetime,
            'timestamp': self._generate_timestamp,
            'time': self._generate_time,
            'year': self._generate_year,
            'enum': self._generate_enum,
            'set': self._generate_set,
            'bit': self._generate_bit,
            'boolean': self._generate_boolean,
            'bool': self._generate_boolean,
            'json': self._generate_json,
            'binary': self._generate_binary,
            'varbinary': self._generate_varbinary,
            'blob': self._generate_blob,
            'tinyblob': self._generate_tinyblob,
            'mediumblob': self._generate_mediumblob,
            'longblob': self._generate_longblob,
            'point': self._generate_point,
            'polygon': self._generate_polygon,
            'linestring': self._generate_linestring,
        }

    def get_check_constraints(self, table_name, column_name):
        """
        Get check constraints for a specific column

        Args:
            table_name (str): Table name
            column_name (str): Column name

        Returns:
            list: List of check constraints for the column
        """
        if not self.schema_analyzer or not hasattr(self.schema_analyzer, 'check_constraints'):
            return []

        # Get all check constraints for the table
        table_constraints = self.schema_analyzer.check_constraints.get(table_name, [])

        # Filter constraints for the specific column
        column_constraints = [
            constraint for constraint in table_constraints
            if constraint.get('column') == column_name
        ]

        return column_constraints

    def generate_value(self, column_info, table_name=None, current_record=None):
        """
        Generate a value for a column based on its type and constraints

        Args:
            column_info (dict): Column information from information_schema
            table_name (str, optional): Table name for check constraint lookup
            current_record (dict, optional): Current record being generated, for related fields

        Returns:
            object: Generated value
        """
        data_type = column_info['data_type'].lower()
        column_type = column_info['column_type'].lower() if column_info['column_type'] else ''
        is_nullable = column_info['is_nullable'].lower() == 'yes'
        column_comment = column_info['column_comment'] if column_info['column_comment'] else ''
        column_name = column_info['column_name']

        # Store the current record for use by generators
        if current_record is not None:
            self._current_record = current_record

        # Special handling for nullable fields that should be NULL in specific cases
        if is_nullable:
            # For events.recurrence_end_date, make it NULL if recurrence_pattern is NULL
            if column_name == 'recurrence_end_date' and table_name == 'events':
                if hasattr(self, '_current_record') and self._current_record.get('recurrence_pattern') is None:
                    return None

            # For schedule_exceptions.start_time and end_time, make them NULL if is_working is 0
            if (column_name == 'start_time' or column_name == 'end_time') and table_name == 'schedule_exceptions':
                if hasattr(self, '_current_record') and self._current_record.get('is_working') == 0:
                    return None

            # For events.start_time and end_time, make them NULL if is_all_day is 1
            if (column_name == 'start_time' or column_name == 'end_time') and table_name == 'events':
                if hasattr(self, '_current_record') and self._current_record.get('is_all_day') == 1:
                    return None

            # Special case for product_inventory.reorder_threshold
            # This column has a CHECK constraint that requires it to be > 0 when not NULL
            # We'll make it NULL 20% of the time to ensure we get enough valid records
            if column_name == 'reorder_threshold' and table_name == 'product_inventory':
                if random.random() < 0.2:
                    return None

            # General case: 10% chance of NULL for nullable columns
            if random.random() < 0.1:
                return None

        # Get check constraints for this column if table_name is provided
        check_constraints = []
        if table_name and self.schema_analyzer:
            check_constraints = self.get_check_constraints(table_name, column_name)
            if check_constraints:
                logging.debug(f"Found {len(check_constraints)} check constraints for {table_name}.{column_name}")

        # Add check constraints to column_info for use by generators
        column_info['check_constraints'] = check_constraints

        # Add table_name to column_info for use by generators
        if table_name:
            column_info['table_name'] = table_name

        # Check for specific generators based on data type
        if data_type in self.type_generators:
            value = self.type_generators[data_type](column_info, column_type, column_comment)

            # Store the generated value in the current record for use by related fields
            if hasattr(self, '_current_record'):
                self._current_record[column_name] = value

            return value

        # Default fallback
        logging.warning(f"No specific generator for type {data_type}, using default string")
        return self.faker.word()

    def _generate_varchar(self, column_info, column_type, column_comment):
        # Extract length from column_type (e.g., varchar(255))
        length_match = re.search(r'varchar\((\d+)\)', column_type)
        max_length = int(length_match.group(1)) if length_match else 255

        # Ensure minimum length of 5 characters
        min_length = min(5, max_length)

        # Generate text with appropriate length
        if max_length <= 10:
            return self.faker.pystr(min_length, max_length)
        elif max_length <= 30:
            return self.faker.word()[:max_length]
        elif max_length <= 100:
            return self.faker.sentence(nb_words=5)[:max_length]
        else:
            return self.faker.text(max_nb_chars=max_length)

    def _generate_char(self, column_info, column_type, column_comment):
        # Extract length from column_type (e.g., char(10))
        length_match = re.search(r'char\((\d+)\)', column_type)
        length = int(length_match.group(1)) if length_match else 1

        # Generate fixed-length string
        return self.faker.pystr(length, length)

    def _generate_text(self, column_info, column_type, column_comment):
        # TEXT type has max length of 65,535 bytes
        # Generate a reasonable length text (not too long)
        min_length = 5  # Minimum 5 characters
        max_length = 1000  # Reasonable max length
        return self.faker.text(max_nb_chars=random.randint(min_length, max_length))

    def _generate_tinytext(self, column_info, column_type, column_comment):
        # TINYTEXT has max length of 255 bytes
        min_length = 5
        max_length = 255
        return self.faker.text(max_nb_chars=random.randint(min_length, max_length))

    def _generate_mediumtext(self, column_info, column_type, column_comment):
        # MEDIUMTEXT has max length of 16,777,215 bytes
        # Generate a reasonable length text (not too long)
        min_length = 5
        max_length = 2000
        return self.faker.text(max_nb_chars=random.randint(min_length, max_length))

    def _generate_longtext(self, column_info, column_type, column_comment):
        # LONGTEXT has max length of 4,294,967,295 bytes
        # Generate a reasonable length text (not too long)
        min_length = 5
        max_length = 4096  # Limit to 4KB as per requirements
        return self.faker.text(max_nb_chars=random.randint(min_length, max_length))

    def _generate_int(self, column_info, column_type, column_comment):
        # Check for unsigned flag
        is_unsigned = 'unsigned' in column_type

        # Default INT range
        min_val = 0 if is_unsigned else -2147483648
        max_val = 4294967295 if is_unsigned else 2147483647

        # Check for BETWEEN constraint in comment
        between_match = re.search(r'between\s+(-?\d+)\s*-\s*(-?\d+)', column_comment.lower())
        if between_match:
            min_val = int(between_match.group(1))
            max_val = int(between_match.group(2))

        # Check column name for common patterns that suggest specific ranges
        column_name_lower = column_info['column_name'].lower()

        # Handle ID columns (usually positive, reasonable values)
        if column_name_lower.endswith('_id') or column_name_lower == 'id':
            min_val = 1
            max_val = min(max_val, 10000)  # Keep IDs in a reasonable range

        # Handle count, quantity columns (usually positive)
        if any(term in column_name_lower for term in ['count', 'quantity', 'num', 'amount']):
            min_val = 0
            max_val = min(max_val, 1000)  # Keep counts reasonable

        # Handle year columns (realistic years)
        if 'year' in column_name_lower:
            min_val = 1970
            max_val = 2030

        # Handle age columns (realistic ages)
        if 'age' in column_name_lower:
            min_val = 0
            max_val = 120

        # Handle bandwidth, storage, memory limits (usually positive, reasonable values)
        if any(term in column_name_lower for term in ['bandwidth', 'storage', 'memory', 'size', 'capacity']):
            min_val = 0
            # Keep values reasonable based on unit
            if 'gb' in column_name_lower:
                max_val = min(max_val, 1000)
            elif 'mb' in column_name_lower:
                max_val = min(max_val, 10000)
            elif 'kb' in column_name_lower:
                max_val = min(max_val, 100000)
            else:
                max_val = min(max_val, 10000)

        # Special case for product_inventory.reorder_threshold
        # This column has a CHECK constraint that requires it to be > 0
        if column_name_lower == 'reorder_threshold' and column_info.get('table_name') == 'product_inventory':
            min_val = 1  # Ensure it's greater than 0 to satisfy the CHECK constraint
            max_val = min(max_val, 100)  # Keep it reasonable

        # Check for check constraints
        check_constraints = column_info.get('check_constraints', [])
        for constraint in check_constraints:
            constraint_type = constraint.get('type')

            # Handle range constraints
            if constraint_type in ('range', 'between') and constraint.get('min_value') is not None and constraint.get('max_value') is not None:
                constraint_min = int(constraint.get('min_value'))
                constraint_max = int(constraint.get('max_value'))
                min_val = max(min_val, constraint_min)
                max_val = min(max_val, constraint_max)
                logging.debug(f"Applied {constraint_type} check constraint to {column_info['column_name']}: {constraint_min} to {constraint_max}")

            # Handle IN constraints
            elif constraint_type == 'in' and constraint.get('allowed_values'):
                allowed_values = [int(v) for v in constraint.get('allowed_values') if str(v).isdigit()]
                if allowed_values:
                    return random.choice(allowed_values)

            # Handle equality constraints
            elif constraint_type == 'equality' and constraint.get('allowed_values'):
                allowed_values = [int(v) for v in constraint.get('allowed_values') if str(v).isdigit()]
                if allowed_values:
                    return allowed_values[0]  # There should be only one value

            # Handle unknown constraints that might be BETWEEN constraints
            elif constraint_type == 'unknown' and constraint.get('raw_clause'):
                # Try to extract BETWEEN pattern from raw clause
                raw_clause = constraint.get('raw_clause', '')
                between_match = re.search(r'BETWEEN\s+(\d+\.?\d*)\s+AND\s+(\d+\.?\d*)', raw_clause, re.IGNORECASE)
                if between_match:
                    min_val = max(min_val, float(between_match.group(1)))
                    max_val = min(max_val, float(between_match.group(2)))
                    logging.debug(f"Applied BETWEEN constraint from raw clause to {column_info['column_name']}: {min_val} to {max_val}")

                # Try to extract >= pattern
                min_match = re.search(r'>=\s*(-?\d+\.?\d*)', raw_clause, re.IGNORECASE)
                if min_match:
                    constraint_min = float(min_match.group(1))
                    min_val = max(min_val, constraint_min)
                    logging.debug(f"Applied >= constraint from raw clause to {column_info['column_name']}: min = {min_val}")

                # Try to extract <= pattern
                max_match = re.search(r'<=\s*(-?\d+\.?\d*)', raw_clause, re.IGNORECASE)
                if max_match:
                    constraint_max = float(max_match.group(1))
                    max_val = min(max_val, constraint_max)
                    logging.debug(f"Applied <= constraint from raw clause to {column_info['column_name']}: max = {max_val}")

                # Try to extract > pattern
                min_match = re.search(r'>\s*(-?\d+\.?\d*)', raw_clause, re.IGNORECASE)
                if min_match:
                    constraint_min = float(min_match.group(1))
                    # Add 1 to ensure it's strictly greater than
                    min_val = max(min_val, constraint_min + 1)
                    logging.debug(f"Applied > constraint from raw clause to {column_info['column_name']}: min = {min_val}")

                # Try to extract < pattern
                max_match = re.search(r'<\s*(-?\d+\.?\d*)', raw_clause, re.IGNORECASE)
                if max_match:
                    constraint_max = float(max_match.group(1))
                    # Subtract 1 to ensure it's strictly less than
                    max_val = min(max_val, constraint_max - 1)
                    logging.debug(f"Applied < constraint from raw clause to {column_info['column_name']}: max = {max_val}")

        return random.randint(min_val, max_val)

    def _generate_tinyint(self, column_info, column_type, column_comment):
        # Check for unsigned flag
        is_unsigned = 'unsigned' in column_type

        # TINYINT range
        min_val = 0 if is_unsigned else -128
        max_val = 255 if is_unsigned else 127

        # Check for BETWEEN constraint in comment
        between_match = re.search(r'between\s+(-?\d+)\s*-\s*(-?\d+)', column_comment.lower())
        if between_match:
            min_val = int(between_match.group(1))
            max_val = int(between_match.group(2))

        # Check column name for common patterns that suggest specific ranges
        column_name_lower = column_info['column_name'].lower()

        # Special case for TINYINT(1) which is often used as boolean
        if '(1)' in column_type:
            # Check if column name suggests a boolean
            if any(term in column_name_lower for term in ['is_', 'has_', 'can_', 'should_', 'flag', 'enabled', 'active', 'status']):
                return random.randint(0, 1)
            # Otherwise treat as a small number
            return random.randint(0, 1)

        # Handle percentage fields (usually 0-100)
        if 'percent' in column_name_lower:
            min_val = 0
            max_val = min(max_val, 100)

        # Handle priority, level, rating fields (usually small positive numbers)
        if any(term in column_name_lower for term in ['priority', 'level', 'rating', 'rank']):
            min_val = 0
            max_val = min(max_val, 10)

        # Handle count, quantity columns (usually positive)
        if any(term in column_name_lower for term in ['count', 'quantity', 'num']):
            min_val = 0

        return random.randint(min_val, max_val)

    def _generate_smallint(self, column_info, column_type, column_comment):
        # Check for unsigned flag
        is_unsigned = 'unsigned' in column_type

        # SMALLINT range
        min_val = 0 if is_unsigned else -32768
        max_val = 65535 if is_unsigned else 32767

        # Check for BETWEEN constraint in comment
        between_match = re.search(r'between\s+(-?\d+)\s*-\s*(-?\d+)', column_comment.lower())
        if between_match:
            min_val = int(between_match.group(1))
            max_val = int(between_match.group(2))

        # Check column name for common patterns that suggest specific ranges
        column_name_lower = column_info['column_name'].lower()

        # Handle ID columns (usually positive, reasonable values)
        if column_name_lower.endswith('_id') or column_name_lower == 'id':
            min_val = 1
            max_val = min(max_val, 10000)  # Keep IDs in a reasonable range

        # Handle port numbers (1-65535, typically in specific ranges)
        if 'port' in column_name_lower:
            min_val = 1
            max_val = min(max_val, 65535)
            # Common port ranges
            if 'http' in column_name_lower:
                min_val = 80
                max_val = 8080
            elif 'db' in column_name_lower or 'sql' in column_name_lower:
                min_val = 3306
                max_val = 5432

        # Handle year columns (realistic years)
        if 'year' in column_name_lower:
            min_val = 1970
            max_val = 2030

        # Handle bandwidth, storage, memory limits (usually positive, reasonable values)
        if any(term in column_name_lower for term in ['bandwidth', 'storage', 'memory', 'size', 'capacity']):
            min_val = 0
            # Keep values reasonable based on unit
            if 'gb' in column_name_lower:
                max_val = min(max_val, 1000)
            elif 'mb' in column_name_lower:
                max_val = min(max_val, 10000)

        return random.randint(min_val, max_val)

    def _generate_mediumint(self, column_info, column_type, column_comment):
        # Check for unsigned flag
        is_unsigned = 'unsigned' in column_type

        # MEDIUMINT range
        min_val = 0 if is_unsigned else -8388608
        max_val = 16777215 if is_unsigned else 8388607

        # Check for BETWEEN constraint in comment
        between_match = re.search(r'between\s+(-?\d+)\s*-\s*(-?\d+)', column_comment.lower())
        if between_match:
            min_val = int(between_match.group(1))
            max_val = int(between_match.group(2))

        # Check column name for common patterns that suggest specific ranges
        column_name_lower = column_info['column_name'].lower()

        # Handle ID columns (usually positive, reasonable values)
        if column_name_lower.endswith('_id') or column_name_lower == 'id':
            min_val = 1
            max_val = min(max_val, 1000000)  # Keep IDs in a reasonable range

        # Handle bandwidth, storage, memory limits (usually positive, reasonable values)
        if any(term in column_name_lower for term in ['bandwidth', 'storage', 'memory', 'size', 'capacity']):
            min_val = 0
            # Keep values reasonable based on unit
            if 'gb' in column_name_lower:
                max_val = min(max_val, 1000)
            elif 'mb' in column_name_lower:
                max_val = min(max_val, 10000)
            elif 'kb' in column_name_lower:
                max_val = min(max_val, 100000)
            else:
                max_val = min(max_val, 10000)

        # Handle 'max' or 'limit' columns (usually positive, reasonable values)
        if any(term in column_name_lower for term in ['max', 'limit', 'quota']):
            min_val = 0
            # If it's a bandwidth limit, keep it reasonable
            if 'bandwidth' in column_name_lower and 'gb' in column_name_lower:
                max_val = min(max_val, 1000)  # Max 1000 GB

        return random.randint(min_val, max_val)

    def _generate_bigint(self, column_info, column_type, column_comment):
        # Check for unsigned flag
        is_unsigned = 'unsigned' in column_type

        # Use a smaller range for practical purposes to avoid overflow issues
        practical_min = 0 if is_unsigned else -1000000000000
        practical_max = 1000000000000

        # Check for BETWEEN constraint in comment
        between_match = re.search(r'between\s+(-?\d+)\s*-\s*(-?\d+)', column_comment.lower())
        if between_match:
            practical_min = int(between_match.group(1))
            practical_max = int(between_match.group(2))

        # Check column name for common patterns that suggest specific ranges
        column_name_lower = column_info['column_name'].lower()

        # Handle ID columns (usually positive, reasonable values)
        if column_name_lower.endswith('_id') or column_name_lower == 'id':
            practical_min = 1
            practical_max = min(practical_max, 1000000000)  # Keep IDs in a reasonable range

        # Handle timestamp-like columns (Unix timestamps)
        if 'timestamp' in column_name_lower or 'time' in column_name_lower:
            # Unix timestamps (seconds since 1970)
            if 'sec' in column_name_lower:
                practical_min = 0  # Jan 1, 1970
                practical_max = 2147483647  # Jan 19, 2038 (max 32-bit timestamp)
            # Millisecond timestamps
            elif 'milli' in column_name_lower or 'ms' in column_name_lower:
                practical_min = 0
                practical_max = 2147483647000  # Same max date but in milliseconds

        # Handle bandwidth, storage, memory limits (usually positive, reasonable values)
        if any(term in column_name_lower for term in ['bandwidth', 'storage', 'memory', 'size', 'capacity']):
            practical_min = 0
            # Keep values reasonable based on unit
            if 'gb' in column_name_lower:
                practical_max = min(practical_max, 10000)  # 10TB in GB
            elif 'mb' in column_name_lower:
                practical_max = min(practical_max, 10000000)  # 10TB in MB
            elif 'kb' in column_name_lower:
                practical_max = min(practical_max, 10000000000)  # 10TB in KB

        # Handle 'max' or 'limit' columns (usually positive, reasonable values)
        if any(term in column_name_lower for term in ['max', 'limit', 'quota']):
            practical_min = 0
            # If it's a bandwidth limit, keep it reasonable
            if 'bandwidth' in column_name_lower and 'gb' in column_name_lower:
                practical_max = min(practical_max, 10000)  # Max 10TB

        return random.randint(practical_min, practical_max)

    def _generate_float(self, column_info, column_type, column_comment):
        # Check for unsigned flag
        is_unsigned = 'unsigned' in column_type

        # Default range - use more reasonable limits to avoid overflow
        min_val = 0.0 if is_unsigned else -1000000.0
        max_val = 1000000.0

        # Check for BETWEEN constraint in comment
        between_match = re.search(r'between\s+(-?\d+\.?\d*)\s*-\s*(-?\d+\.?\d*)', column_comment.lower())
        if between_match:
            min_val = float(between_match.group(1))
            max_val = float(between_match.group(2))

        # Check column name for common patterns that suggest specific ranges
        column_name_lower = column_info['column_name'].lower()

        # Handle percentage fields (usually 0-100 or 0-1)
        if 'percent' in column_name_lower or 'discount' in column_name_lower:
            min_val = 0.0
            if max_val > 100:  # If the field can store values > 100
                max_val = 100.0
            elif max_val <= 1:  # If the field is likely storing 0-1 range
                max_val = 1.0

        # Handle price, cost, amount fields (usually positive)
        if any(term in column_name_lower for term in ['price', 'cost', 'amount', 'fee']):
            min_val = max(0.0, min_val)
            # Keep prices reasonable
            if 'price' in column_name_lower and max_val > 10000:
                max_val = min(max_val, 10000.0)

        # Handle ratio, factor fields (usually small values)
        if any(term in column_name_lower for term in ['ratio', 'factor', 'multiplier']):
            min_val = max(-100.0, min_val)
            max_val = min(max_val, 100.0)

        # Handle coordinate fields (latitude/longitude)
        if 'lat' in column_name_lower:
            min_val = -90.0
            max_val = 90.0
        elif 'lon' in column_name_lower or 'lng' in column_name_lower:
            min_val = -180.0
            max_val = 180.0

        # Handle bandwidth, storage, memory limits (usually positive, reasonable values)
        if any(term in column_name_lower for term in ['bandwidth', 'storage', 'memory', 'size', 'capacity']):
            min_val = 0.0
            # Keep values reasonable based on unit
            if 'gb' in column_name_lower:
                max_val = min(max_val, 1000.0)
            elif 'mb' in column_name_lower:
                max_val = min(max_val, 10000.0)

        # Check for check constraints
        check_constraints = column_info.get('check_constraints', [])
        for constraint in check_constraints:
            constraint_type = constraint.get('type')

            # Handle range constraints
            if constraint_type in ('range', 'between') and constraint.get('min_value') is not None and constraint.get('max_value') is not None:
                constraint_min = float(constraint.get('min_value'))
                constraint_max = float(constraint.get('max_value'))
                min_val = max(min_val, constraint_min)
                max_val = min(max_val, constraint_max)
                logging.debug(f"Applied {constraint_type} check constraint to {column_info['column_name']}: {constraint_min} to {constraint_max}")

            # Handle IN constraints
            elif constraint_type == 'in' and constraint.get('allowed_values'):
                try:
                    allowed_values = [float(v) for v in constraint.get('allowed_values')]
                    if allowed_values:
                        return random.choice(allowed_values)
                except (ValueError, TypeError):
                    pass

            # Handle equality constraints
            elif constraint_type == 'equality' and constraint.get('allowed_values'):
                try:
                    allowed_values = [float(v) for v in constraint.get('allowed_values')]
                    if allowed_values:
                        return allowed_values[0]  # There should be only one value
                except (ValueError, TypeError):
                    pass

            # Handle unknown constraints that might be BETWEEN constraints
            elif constraint_type == 'unknown' and constraint.get('raw_clause'):
                # Try to extract BETWEEN pattern from raw clause
                raw_clause = constraint.get('raw_clause', '')
                between_match = re.search(r'BETWEEN\s+(\d+\.?\d*)\s+AND\s+(\d+\.?\d*)', raw_clause, re.IGNORECASE)
                if between_match:
                    constraint_min = float(between_match.group(1))
                    constraint_max = float(between_match.group(2))
                    min_val = max(min_val, constraint_min)
                    max_val = min(max_val, constraint_max)
                    logging.debug(f"Applied BETWEEN constraint from raw clause to {column_info['column_name']}: {min_val} to {max_val}")

                # Try to extract >= pattern
                min_match = re.search(r'>=\s*(-?\d+\.?\d*)', raw_clause, re.IGNORECASE)
                if min_match:
                    constraint_min = float(min_match.group(1))
                    min_val = max(min_val, constraint_min)
                    logging.debug(f"Applied >= constraint from raw clause to {column_info['column_name']}: min = {min_val}")

                # Try to extract <= pattern
                max_match = re.search(r'<=\s*(-?\d+\.?\d*)', raw_clause, re.IGNORECASE)
                if max_match:
                    constraint_max = float(max_match.group(1))
                    max_val = min(max_val, constraint_max)
                    logging.debug(f"Applied <= constraint from raw clause to {column_info['column_name']}: max = {max_val}")

                # Try to extract > pattern
                min_match = re.search(r'>\s*(-?\d+\.?\d*)', raw_clause, re.IGNORECASE)
                if min_match:
                    constraint_min = float(min_match.group(1))
                    # Add a small epsilon to ensure it's strictly greater than
                    min_val = max(min_val, constraint_min + 0.000001)
                    logging.debug(f"Applied > constraint from raw clause to {column_info['column_name']}: min = {min_val}")

                # Try to extract < pattern
                max_match = re.search(r'<\s*(-?\d+\.?\d*)', raw_clause, re.IGNORECASE)
                if max_match:
                    constraint_max = float(max_match.group(1))
                    # Subtract a small epsilon to ensure it's strictly less than
                    max_val = min(max_val, constraint_max - 0.000001)
                    logging.debug(f"Applied < constraint from raw clause to {column_info['column_name']}: max = {max_val}")

        return round(random.uniform(min_val, max_val), 6)

    def _generate_double(self, column_info, column_type, column_comment):
        # Similar to float but with higher precision
        return self._generate_float(column_info, column_type, column_comment)

    def _generate_decimal(self, column_info, column_type, column_comment):
        # Extract precision and scale from column_type (e.g., decimal(10,2))
        precision_scale_match = re.search(r'decimal\((\d+),(\d+)\)', column_type)

        if precision_scale_match:
            precision = int(precision_scale_match.group(1))
            scale = int(precision_scale_match.group(2))

            # Calculate max value based on precision and scale
            max_digits = precision - scale

            # Calculate the maximum value more carefully to avoid overflow
            # For example, decimal(5,2) can store values from -999.99 to 999.99
            max_int_part = int('9' * max_digits) if max_digits > 0 else 0

            # Set reasonable limits to avoid out of range errors
            max_val = float(max_int_part + (int('9' * scale) / (10 ** scale)) if scale > 0 else max_int_part)
            min_val = -max_val if 'unsigned' not in column_type else 0

            # Check for BETWEEN constraint in comment
            between_match = re.search(r'between\s+(-?\d+\.?\d*)\s*-\s*(-?\d+\.?\d*)', column_comment.lower())
            if between_match:
                min_val = float(between_match.group(1))
                max_val = float(between_match.group(2))

            # Check column name for common patterns that suggest specific ranges
            column_name_lower = column_info['column_name'].lower()

            # Handle percentage fields (usually 0-100 or 0-1)
            if 'percent' in column_name_lower or 'discount' in column_name_lower:
                if max_val > 100:  # If the field can store values > 100
                    max_val = 100.0
                    min_val = max(0.0, min_val)
                elif max_val <= 1:  # If the field is likely storing 0-1 range
                    max_val = 1.0
                    min_val = 0.0

            # Handle price, cost, amount fields (usually positive)
            if any(term in column_name_lower for term in ['price', 'cost', 'amount', 'fee']):
                min_val = max(0.0, min_val)
                # Keep prices reasonable
                if 'price' in column_name_lower and max_val > 10000:
                    max_val = min(max_val, 10000.0)

            # Handle credit limit fields (usually 0-10000)
            if 'credit' in column_name_lower and 'limit' in column_name_lower:
                min_val = max(0.0, min_val)
                max_val = min(max_val, 10000.0)
                logging.debug(f"Applied credit limit heuristic to {column_info['column_name']}: {min_val} to {max_val}")

            # Handle bandwidth, storage, memory limits (usually positive, reasonable values)
            if any(term in column_name_lower for term in ['bandwidth', 'storage', 'memory', 'size', 'capacity']):
                min_val = max(0.0, min_val)
                # Keep values reasonable based on unit
                if 'gb' in column_name_lower and max_val > 1000:
                    max_val = min(max_val, 1000.0)
                elif 'mb' in column_name_lower and max_val > 10000:
                    max_val = min(max_val, 10000.0)
                elif 'kb' in column_name_lower and max_val > 100000:
                    max_val = min(max_val, 100000.0)

            # Check for check constraints
            check_constraints = column_info.get('check_constraints', [])
            for constraint in check_constraints:
                constraint_type = constraint.get('type')

                # Handle range constraints
                if constraint_type in ('range', 'between') and constraint.get('min_value') is not None and constraint.get('max_value') is not None:
                    constraint_min = float(constraint.get('min_value'))
                    constraint_max = float(constraint.get('max_value'))
                    min_val = max(min_val, constraint_min)
                    max_val = min(max_val, constraint_max)
                    logging.debug(f"Applied {constraint_type} check constraint to {column_info['column_name']}: {constraint_min} to {constraint_max}")

                # Handle IN constraints
                elif constraint_type == 'in' and constraint.get('allowed_values'):
                    try:
                        allowed_values = [float(v) for v in constraint.get('allowed_values')]
                        if allowed_values:
                            value = random.choice(allowed_values)
                            return Decimal(str(value))
                    except (ValueError, TypeError):
                        pass

                # Handle equality constraints
                elif constraint_type == 'equality' and constraint.get('allowed_values'):
                    try:
                        allowed_values = [float(v) for v in constraint.get('allowed_values')]
                        if allowed_values:
                            return Decimal(str(allowed_values[0]))  # There should be only one value
                    except (ValueError, TypeError):
                        pass

                # Handle unknown constraints that might be BETWEEN constraints
                elif constraint_type == 'unknown' and constraint.get('raw_clause'):
                    # Try to extract BETWEEN pattern from raw clause
                    raw_clause = constraint.get('raw_clause', '')
                    logging.debug(f"Processing unknown constraint raw clause for {column_info['column_name']}: {raw_clause}")

                    # Try to extract BETWEEN pattern
                    between_match = re.search(r'BETWEEN\s+(\d+\.?\d*)\s+AND\s+(\d+\.?\d*)', raw_clause, re.IGNORECASE)
                    if between_match:
                        constraint_min = float(between_match.group(1))
                        constraint_max = float(between_match.group(2))
                        min_val = max(min_val, constraint_min)
                        max_val = min(max_val, constraint_max)
                        logging.debug(f"Applied BETWEEN constraint from raw clause to {column_info['column_name']}: {min_val} to {max_val}")

                    # Try to extract >= and <= patterns
                    min_match = re.search(r'>=\s*(-?\d+\.?\d*)', raw_clause, re.IGNORECASE)
                    max_match = re.search(r'<=\s*(-?\d+\.?\d*)', raw_clause, re.IGNORECASE)

                    if min_match:
                        constraint_min = float(min_match.group(1))
                        min_val = max(min_val, constraint_min)
                        logging.debug(f"Applied >= constraint from raw clause to {column_info['column_name']}: min = {min_val}")

                    if max_match:
                        constraint_max = float(max_match.group(1))
                        max_val = min(max_val, constraint_max)
                        logging.debug(f"Applied <= constraint from raw clause to {column_info['column_name']}: max = {max_val}")

                    # Try to extract > pattern
                    min_match = re.search(r'>\s*(-?\d+\.?\d*)', raw_clause, re.IGNORECASE)
                    if min_match:
                        constraint_min = float(min_match.group(1))
                        # Add a small epsilon to ensure it's strictly greater than
                        min_val = max(min_val, constraint_min + Decimal('0.000001'))
                        logging.debug(f"Applied > constraint from raw clause to {column_info['column_name']}: min = {min_val}")

                    # Try to extract < pattern
                    max_match = re.search(r'<\s*(-?\d+\.?\d*)', raw_clause, re.IGNORECASE)
                    if max_match:
                        constraint_max = float(max_match.group(1))
                        # Subtract a small epsilon to ensure it's strictly less than
                        max_val = min(max_val, constraint_max - Decimal('0.000001'))
                        logging.debug(f"Applied < constraint from raw clause to {column_info['column_name']}: max = {max_val}")

            # Generate a random decimal value within the safe range
            value = random.uniform(min_val, max_val)

            # Format to the correct scale
            return Decimal(str(round(value, scale)))
        else:
            # Default decimal with reasonable precision
            return Decimal(str(round(random.uniform(0, 100), 2)))

    def _generate_date(self, column_info, column_type, column_comment):
        # Generate a random date within the last 10 years
        start_date = datetime.now() - timedelta(days=3650)  # ~10 years ago
        end_date = datetime.now() + timedelta(days=365)     # 1 year in the future

        # Check if this is a related date field (like end_date that should be after start_date)
        column_name = column_info['column_name'].lower()
        table_name = column_info.get('table_name', '').lower()

        # Handle specific temporal relationships based on column and table names
        if column_name == 'end_date' and table_name == 'events':
            # For events.end_date, ensure it's >= events.start_date
            # Try to find the start_date value in the same record
            if hasattr(self, '_current_record') and self._current_record.get('start_date'):
                start_date_val = self._current_record.get('start_date')
                # Generate a date that's either the same or later than start_date
                days_to_add = random.randint(0, 30)  # 0-30 days after start_date
                return start_date_val + timedelta(days=days_to_add)

        elif column_name == 'recurrence_end_date' and table_name == 'events':
            # For events.recurrence_end_date, ensure it's >= events.end_date if not NULL
            if hasattr(self, '_current_record') and self._current_record.get('end_date'):
                end_date_val = self._current_record.get('end_date')
                # Generate a date that's either the same or later than end_date
                days_to_add = random.randint(0, 90)  # 0-90 days after end_date
                return end_date_val + timedelta(days=days_to_add)

        elif column_name == 'effective_to' and table_name == 'schedules':
            # For schedules.effective_to, ensure it's > schedules.effective_from if not NULL
            if hasattr(self, '_current_record') and self._current_record.get('effective_from'):
                effective_from_val = self._current_record.get('effective_from')
                # Generate a date that's later than effective_from
                days_to_add = random.randint(1, 180)  # 1-180 days after effective_from
                return effective_from_val + timedelta(days=days_to_add)

        elif column_name == 'termination_date' and table_name == 'employees':
            # For employees.termination_date, ensure it's >= employees.hire_date if not NULL
            if hasattr(self, '_current_record') and self._current_record.get('hire_date'):
                hire_date_val = self._current_record.get('hire_date')
                # Generate a date that's either the same or later than hire_date
                days_to_add = random.randint(0, 3650)  # 0-10 years after hire_date
                return hire_date_val + timedelta(days=days_to_add)

        random_date = start_date + timedelta(
            days=random.randint(0, (end_date - start_date).days)
        )

        return random_date.date()

    def _generate_datetime(self, column_info, column_type, column_comment):
        # Generate a random datetime within the last 10 years
        start_date = datetime.now() - timedelta(days=3650)  # ~10 years ago
        end_date = datetime.now() + timedelta(days=365)     # 1 year in the future

        # Check if this is a related datetime field
        column_name = column_info['column_name'].lower()
        table_name = column_info.get('table_name', '').lower()

        # Handle specific temporal relationships based on column and table names
        if column_name == 'end_datetime' and table_name == 'appointments':
            # For appointments.end_datetime, ensure it's > appointments.start_datetime
            if hasattr(self, '_current_record') and self._current_record.get('start_datetime'):
                start_datetime_val = self._current_record.get('start_datetime')
                # Generate a datetime that's later than start_datetime
                minutes_to_add = random.randint(15, 180)  # 15 minutes to 3 hours after start_datetime
                return start_datetime_val + timedelta(minutes=minutes_to_add)

        random_date = start_date + timedelta(
            days=random.randint(0, (end_date - start_date).days),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59)
        )

        return random_date

    def _generate_timestamp(self, column_info, column_type, column_comment):
        # Similar to datetime but within the valid timestamp range
        start_date = datetime(1970, 1, 1)
        end_date = datetime(2038, 1, 19)

        random_date = start_date + timedelta(
            days=random.randint(0, (end_date - start_date).days),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59)
        )

        return random_date

    def _generate_time(self, column_info, column_type, column_comment):
        # Generate a random time
        hours = random.randint(0, 23)
        minutes = random.randint(0, 59)
        seconds = random.randint(0, 59)

        # Check if this is a related time field
        column_name = column_info['column_name'].lower()
        table_name = column_info.get('table_name', '').lower()

        # Handle specific temporal relationships based on column and table names
        if column_name == 'end_time' and (table_name == 'events' or table_name == 'schedules' or table_name == 'schedule_exceptions'):
            # For end_time, ensure it's > start_time
            if hasattr(self, '_current_record') and self._current_record.get('start_time'):
                start_time_str = self._current_record.get('start_time')

                # Parse the start_time string
                if isinstance(start_time_str, str):
                    start_hours, start_minutes, start_seconds = map(int, start_time_str.split(':'))

                    # Ensure end_time is later than start_time
                    # Add at least 15 minutes, up to 8 hours
                    minutes_to_add = random.randint(15, 480)

                    # Calculate new time
                    total_minutes = start_hours * 60 + start_minutes + minutes_to_add
                    end_hours = (total_minutes // 60) % 24
                    end_minutes = total_minutes % 60

                    return f"{end_hours:02d}:{end_minutes:02d}:{random.randint(0, 59):02d}"

        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def _generate_year(self, column_info, column_type, column_comment):
        # Generate a random year between 1901 and 2155
        return random.randint(1901, 2155)

    def _generate_enum(self, column_info, column_type, column_comment):
        # Extract enum values from column_type (e.g., enum('small','medium','large'))
        enum_match = re.search(r'enum\((.*?)\)', column_type)

        if enum_match:
            # Parse the enum values
            enum_values_str = enum_match.group(1)
            enum_values = [val.strip("'\"") for val in enum_values_str.split(',')]

            # Return a random enum value
            return random.choice(enum_values)
        else:
            return "unknown"

    def _generate_set(self, column_info, column_type, column_comment):
        # Extract set values from column_type (e.g., set('a','b','c'))
        set_match = re.search(r'set\((.*?)\)', column_type)

        if set_match:
            # Parse the set values
            set_values_str = set_match.group(1)
            set_values = [val.strip("'\"") for val in set_values_str.split(',')]

            # Determine how many values to include (0 to all)
            num_values = random.randint(0, len(set_values))

            # Select random values
            selected_values = random.sample(set_values, num_values)

            # Return as comma-separated string
            return ','.join(selected_values)
        else:
            return ""

    def _generate_bit(self, column_info, column_type, column_comment):
        # Extract bit length from column_type (e.g., bit(4))
        bit_match = re.search(r'bit\((\d+)\)', column_type)
        length = int(bit_match.group(1)) if bit_match else 1

        # Generate a random bit value
        max_val = 2 ** length - 1
        return random.randint(0, max_val)

    def _generate_boolean(self, column_info, column_type, column_comment):
        # Generate a random boolean value
        return random.choice([True, False])

    def _generate_json(self, column_info, column_type, column_comment):
        """
        Generate JSON data based on column name and constraints
        """
        import json
        import logging

        column_name = column_info['column_name'].lower()
        table_name = column_info.get('table_name', '').lower()

        logging.info(f"Generating JSON for {table_name}.{column_name}")

        # Check for specific JSON patterns based on column name
        if 'address' in column_name:
            # Generate address JSON with required fields
            data = {
                'street': self.faker.street_address(),
                'city': self.faker.city(),
                'postal_code': self.faker.postcode(),
                'country': self.faker.country(),
                'state': self.faker.state()
            }
            logging.info(f"Generated address JSON: {data}")
        elif 'shipping_address' in column_name or 'billing_address' in column_name:
            # Generate address JSON with required fields
            data = {
                'street': self.faker.street_address(),
                'city': self.faker.city(),
                'postal_code': self.faker.postcode(),
                'country': self.faker.country(),
                'state': self.faker.state()
            }
            logging.info(f"Generated shipping/billing address JSON: {data}")
        elif 'attributes' in column_name and 'product' in table_name:
            # Generate product attributes with required fields
            data = {
                'weight': float(round(random.uniform(0.1, 20.0), 2)),
                'category': random.choice(['Electronics', 'Clothing', 'Home', 'Books', 'Sports']),
                'color': self.faker.color_name(),
                'material': random.choice(['plastic', 'metal', 'wood', 'glass', 'fabric'])
            }
            logging.info(f"Generated product attributes JSON: {data}")
        elif 'payment_details' in column_name:
            # Generate payment details with method field
            data = {
                'method': random.choice(['credit_card', 'paypal', 'bank_transfer', 'cash']),
                'transaction_id': self.faker.uuid4(),
                'status': random.choice(['completed', 'pending', 'failed']),
                'amount': float(round(random.uniform(10, 1000), 2))
            }
            logging.info(f"Generated payment details JSON: {data}")
        elif 'preferences' in column_name:
            # Generate customer preferences
            data = {
                'marketing_emails': random.choice([True, False]),
                'theme': random.choice(['light', 'dark', 'auto']),
                'language': random.choice(['en-US', 'es-ES', 'fr-FR', 'de-DE'])
            }
            logging.info(f"Generated preferences JSON: {data}")
        elif 'options' in column_name:
            # Generate product options as JSON array
            data = [
                {
                    'name': 'color',
                    'values': ['black', 'white', 'red', 'blue', 'green']
                },
                {
                    'name': 'size',
                    'values': ['S', 'M', 'L', 'XL']
                }
            ]
            logging.info(f"Generated options JSON: {data}")
        elif 'dimensions' in column_name:
            # Generate product dimensions
            data = {
                'width': float(round(random.uniform(1, 100), 2)),
                'height': float(round(random.uniform(1, 100), 2)),
                'depth': float(round(random.uniform(1, 100), 2)),
                'unit': 'cm'
            }
            logging.info(f"Generated dimensions JSON: {data}")
        elif 'tags' in column_name:
            # Generate tags as JSON array
            categories = ['electronics', 'clothing', 'home', 'books', 'sports']
            features = ['new', 'sale', 'popular', 'trending', 'limited']
            data = random.sample(categories, random.randint(1, 3)) + random.sample(features, random.randint(1, 2))
            logging.info(f"Generated tags JSON: {data}")
        elif 'selected_options' in column_name:
            # Generate selected product options
            data = {
                'color': random.choice(['black', 'white', 'red', 'blue', 'green']),
                'size': random.choice(['S', 'M', 'L', 'XL'])
            }
            logging.info(f"Generated selected options JSON: {data}")
        elif 'custom_attributes' in column_name:
            # Generate custom product attributes
            data = {
                'gift_wrap': random.choice([True, False]),
                'engraving': self.faker.text(max_nb_chars=20) if random.choice([True, False]) else None,
                'special_instructions': self.faker.text(max_nb_chars=50) if random.choice([True, False]) else None
            }
            logging.info(f"Generated custom attributes JSON: {data}")
        elif 'review_details' in column_name:
            # Generate review details
            data = {
                'verified_purchase': random.choice([True, False]),
                'purchase_date': self.faker.date_time_this_year().strftime('%Y-%m-%d'),
                'pros': self.faker.text(max_nb_chars=50) if random.choice([True, False]) else None,
                'cons': self.faker.text(max_nb_chars=50) if random.choice([True, False]) else None
            }
            logging.info(f"Generated review details JSON: {data}")
        elif 'response' in column_name:
            # Generate seller response
            if random.choice([True, False]):
                data = {
                    'text': self.faker.text(max_nb_chars=100),
                    'date': self.faker.date_time_this_year().strftime('%Y-%m-%d'),
                    'representative': self.faker.name()
                }
                logging.info(f"Generated response JSON: {data}")
            else:
                logging.info("Generated NULL response")
                return None
        elif 'metadata' in column_name:
            # Generate generic metadata
            data = {
                'created_by': self.faker.name(),
                'source': random.choice(['web', 'mobile', 'api', 'store']),
                'version': f"{random.randint(1, 5)}.{random.randint(0, 9)}.{random.randint(0, 9)}",
                'notes': self.faker.text(max_nb_chars=50) if random.choice([True, False]) else None
            }
            logging.info(f"Generated metadata JSON: {data}")
        else:
            # Generate a simple JSON object for other cases
            data = json.loads(self.faker.json())
            logging.info(f"Generated generic JSON: {data}")

        # Convert the Python object to a JSON string
        json_str = json.dumps(data)
        logging.info(f"Converted to JSON string: {json_str}")
        return json_str

    def _generate_binary(self, column_info, column_type, column_comment):
        # Extract length from column_type (e.g., binary(10))
        length_match = re.search(r'binary\((\d+)\)', column_type)
        length = int(length_match.group(1)) if length_match else 1

        # Generate fixed-length binary data
        return bytes([random.randint(0, 255) for _ in range(length)])

    def _generate_varbinary(self, column_info, column_type, column_comment):
        # Extract max length from column_type (e.g., varbinary(100))
        length_match = re.search(r'varbinary\((\d+)\)', column_type)
        max_length = int(length_match.group(1)) if length_match else 255

        # Generate variable-length binary data
        length = random.randint(1, max_length)
        return bytes([random.randint(0, 255) for _ in range(length)])

    def _generate_blob(self, column_info, column_type, column_comment):
        # BLOB has max length of 65,535 bytes
        # Generate a reasonable length blob (not too long)
        length = random.randint(10, 1000)
        return bytes([random.randint(0, 255) for _ in range(length)])

    def _generate_tinyblob(self, column_info, column_type, column_comment):
        # TINYBLOB has max length of 255 bytes
        length = random.randint(5, 255)
        return bytes([random.randint(0, 255) for _ in range(length)])

    def _generate_mediumblob(self, column_info, column_type, column_comment):
        # MEDIUMBLOB has max length of 16,777,215 bytes
        # Generate a reasonable length blob (not too long)
        length = random.randint(10, 2000)
        return bytes([random.randint(0, 255) for _ in range(length)])

    def _generate_longblob(self, column_info, column_type, column_comment):
        # LONGBLOB has max length of 4,294,967,295 bytes
        # Generate a reasonable length blob (not too long)
        length = random.randint(10, 4096)  # Limit to 4KB as per requirements
        return bytes([random.randint(0, 255) for _ in range(length)])

    def _generate_point(self, column_info, column_type, column_comment):
        """
        Generate a MySQL POINT value in WKT format
        """
        # Generate random latitude and longitude within reasonable bounds
        lat = random.uniform(-90, 90)
        lng = random.uniform(-180, 180)

        # Format as WKT (Well-Known Text) POINT
        return f"POINT({lng} {lat})"

    def _generate_polygon(self, column_info, column_type, column_comment):
        """
        Generate a MySQL POLYGON value in WKT format
        """
        # Generate a simple polygon (rectangle)
        # Center point
        center_x = random.uniform(-170, 170)
        center_y = random.uniform(-80, 80)

        # Size of the rectangle (small enough to avoid crossing the date line or poles)
        width = random.uniform(0.1, 10)
        height = random.uniform(0.1, 10)

        # Calculate corners
        x1 = center_x - width/2
        y1 = center_y - height/2
        x2 = center_x + width/2
        y2 = center_y + height/2

        # Format as WKT POLYGON - note that the first and last points must be the same
        return f"POLYGON(({x1} {y1}, {x1} {y2}, {x2} {y2}, {x2} {y1}, {x1} {y1}))"

    def _generate_linestring(self, column_info, column_type, column_comment):
        """
        Generate a MySQL LINESTRING value in WKT format
        """
        # Generate a simple linestring with 3-6 points
        num_points = random.randint(3, 6)

        # Start point
        start_x = random.uniform(-170, 170)
        start_y = random.uniform(-80, 80)

        points = [(start_x, start_y)]

        # Generate additional points with small offsets from the previous point
        for i in range(1, num_points):
            prev_x, prev_y = points[i-1]
            # Add a small random offset
            new_x = prev_x + random.uniform(-5, 5)
            new_y = prev_y + random.uniform(-5, 5)

            # Ensure we stay within valid coordinates
            new_x = max(-180, min(180, new_x))
            new_y = max(-90, min(90, new_y))

            points.append((new_x, new_y))

        # Format as WKT LINESTRING
        points_str = ", ".join([f"{x} {y}" for x, y in points])
        return f"LINESTRING({points_str})"
