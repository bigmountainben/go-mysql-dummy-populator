# MySQL Dummy Data Populator

[![Unit Tests](https://github.com/vitebski/mysql-dummy-populator/actions/workflows/unit-tests.yml/badge.svg?branch=main)](https://github.com/vitebski/mysql-dummy-populator/actions/workflows/unit-tests.yml)
[![E2E Tests](https://github.com/vitebski/mysql-dummy-populator/actions/workflows/e2e-tests.yml/badge.svg?branch=main)](https://github.com/vitebski/mysql-dummy-populator/actions/workflows/e2e-tests.yml)
[![codecov](https://codecov.io/gh/vitebski/mysql-dummy-populator/branch/main/graph/badge.svg)](https://codecov.io/gh/vitebski/mysql-dummy-populator)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![MySQL 8.0+](https://img.shields.io/badge/mysql-8.0+-orange.svg)](https://dev.mysql.com/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Python tool that populates MySQL databases with realistic dummy data, handling foreign keys, circular dependencies, and many-to-many relationships.

## Project Status

The badges at the top of this README provide at-a-glance information about the project:

- **Unit Tests**: Status of the automated unit tests
- **E2E Tests**: Status of the end-to-end tests with a real MySQL database
- **Code Coverage**: Percentage of code covered by tests (tracked by Codecov)
- **Python 3.8+**: Indicates Python version compatibility
- **MySQL 8.0+**: Indicates MySQL version compatibility
- **License: MIT**: Shows the project's license

## Features

- Analyzes database schema to understand table relationships
- Resolves foreign key dependencies and sorts tables in the correct order for population
- Detects and handles circular dependencies
- Identifies many-to-many relationship tables
- Generates realistic fake data using the Faker library
- Supports all MySQL 8 data types
- Honors constraints like NOT NULL, UNIQUE, and CHECK
- Configurable number of records per table
- Detailed logging and error reporting

## Requirements

- Python 3.6+
- MySQL 8.0+
- Required Python packages (see `requirements.txt`)
- For development and testing, additional packages are required (see `requirements-dev.txt`)

## Installation

### Option 1: Install from PyPI (Recommended)

You can install the package directly from PyPI:

```bash
pip install mysql-dummy-populator
```

### Option 2: Install from Source

If you want to install from source:

1. Clone this repository:

   ```bash
   git clone https://github.com/vitebski/mysql-dummy-populator.git
   cd mysql-dummy-populator
   ```

2. Install the package in development mode:

   ```bash
   pip install -e .
   ```

3. Create a `.env` file with your MySQL connection details:

   ```bash
   # Copy the sample file
   cp .env.sample .env

   # Edit the .env file with your database details
   nano .env  # or use your preferred editor
   ```

## Configuration

The tool can be configured in three ways, with the following priority order (highest to lowest):

1. **Command-line arguments**
2. **Environment variables**
3. **.env file**

### .env File Configuration

The tool automatically looks for a `.env` file in the current directory. You can use the provided `.env.sample` as a template:

```env
# MySQL Database Connection
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=your_database
MYSQL_PORT=3306

# Data Generation Settings
MYSQL_RECORDS=10
MYSQL_LOCALE=en_US

# Application Settings
MYSQL_LOG_LEVEL=INFO
```

You can also specify a different `.env` file location using the `--env-file` parameter.

### Environment Variables

All configuration options can be set using environment variables with the `MYSQL_` prefix:

```bash
export MYSQL_HOST=localhost
export MYSQL_USER=root
export MYSQL_PASSWORD=your_password
export MYSQL_DATABASE=your_database
```

## Usage

### Command Line

If you installed the package via pip, you can run the tool directly from the command line:

```bash
mysql-dummy-populator
```

Or specify parameters directly:

```bash
mysql-dummy-populator --host localhost --user root --password your_password --database your_database --records 20
```

You can also specify a custom `.env` file:

```bash
mysql-dummy-populator --env-file /path/to/custom/.env
```

If you installed from source, you can run the tool using:

```bash
# If installed in development mode
mysql-dummy-populator

# Or using the Python module directly
python -m main
```

### Available Options

- `--host`: MySQL host (default: from MYSQL_HOST env var or .env file)
- `--user`: MySQL user (default: from MYSQL_USER env var or .env file)
- `--password`: MySQL password (default: from MYSQL_PASSWORD env var or .env file)
- `--database`: MySQL database name (default: from MYSQL_DATABASE env var or .env file)
- `--port`: MySQL port (default: from MYSQL_PORT env var or .env file, or 3306)
- `--records`: Number of records per table (default: from MYSQL_RECORDS env var or .env file, or 10)
- `--locale`: Locale for fake data generation (default: from MYSQL_LOCALE env var or .env file, or en_US)
- `--log-level`: Log level (default: from MYSQL_LOG_LEVEL env var or .env file, or INFO)
- `--env-file`: Path to .env file (default: .env)
- `--analyze-only`: Only analyze the database schema without populating data

### Analyze-Only Mode

You can use the tool to analyze your database schema without actually populating any data:

```bash
mysql-dummy-populator --analyze-only
```

This will generate a detailed report about your database schema, including:

1. Basic statistics about tables, views, and relationships
2. Table categories (standalone, dependent, many-to-many, circular)
3. Detailed information about circular dependencies
4. Many-to-many relationship tables and their connections
5. Recommended table insertion order for data population
6. Complete ordered list of tables

This mode is useful for understanding complex database schemas and identifying potential issues before populating data.

## How It Works

1. **Schema Analysis**: The tool analyzes your database schema to understand table relationships, foreign keys, and constraints.

2. **Dependency Resolution**: Tables are sorted in an order that respects foreign key dependencies, starting with tables that have no foreign keys.

3. **Circular Dependency Detection**: The tool identifies circular dependencies (e.g., Table A references Table B, which references Table A) and handles them using a multi-pass approach.

4. **Many-to-Many Relationship Handling**: Many-to-many relationship tables are populated after their referenced tables.

5. **Data Generation**: Realistic fake data is generated for each column based on its data type and constraints.

6. **Data Insertion**: Data is inserted into tables in the correct order, ensuring foreign key constraints are satisfied.

## Supported Data Types

The tool supports all MySQL 8 data types, including:

- Numeric types: INT, TINYINT, SMALLINT, MEDIUMINT, BIGINT, FLOAT, DOUBLE, DECIMAL
- String types: CHAR, VARCHAR, TEXT, TINYTEXT, MEDIUMTEXT, LONGTEXT
- Date and time types: DATE, DATETIME, TIMESTAMP, TIME, YEAR
- Binary types: BINARY, VARBINARY, BLOB, TINYBLOB, MEDIUMBLOB, LONGBLOB
- Other types: ENUM, SET, BIT, BOOLEAN, JSON

## Handling Constraints

The tool respects various MySQL constraints:

- **NOT NULL**: Ensures non-null values are generated
- **UNIQUE/PRIMARY KEY**: Generates unique values for these columns
- **FOREIGN KEYS**: References existing values in the referenced tables
- **CHECK**: Honors check constraints (via column comments with BETWEEN)
- **Type Ranges**: Respects the valid ranges for each data type

## Troubleshooting

If you encounter issues:

1. **Check Logs**: Increase log level to DEBUG for more detailed information
2. **Database Permissions**: Ensure the user has sufficient permissions to read schema information and insert data
3. **Circular Dependencies**: Complex circular dependencies might require manual intervention
4. **Memory Usage**: For large databases, consider reducing the number of records per table

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Automated Testing

This project uses GitHub Actions for automated testing to ensure code quality and functionality.

### Unit Tests

The unit tests workflow runs all the unit tests in the project across multiple Python versions:

- Python 3.8
- Python 3.9
- Python 3.10
- Python 3.11

To run the unit tests locally:

```bash
# Activate your virtual environment
source venv/bin/activate

# Run all unit tests
python -m unittest discover -s tests -p "test_*.py"

# Install development dependencies
pip install -r requirements-dev.txt

# Run tests with coverage report
coverage run -m unittest discover -s tests -p "test_*.py"
coverage report

# Note: When running tests, you may see warning and error messages like
# "Verification failed: 1 tables have no records". These are expected and
# are part of testing error handling scenarios, not actual test failures.
```

### Code Coverage

The project uses [Codecov](https://codecov.io) to track code coverage metrics. Coverage reports are automatically generated during the CI process and uploaded to Codecov.

You can view the latest coverage report on the [Codecov dashboard](https://codecov.io/gh/vitebski/mysql-dummy-populator).

To generate a coverage report locally:

```bash
# Activate your virtual environment
source venv/bin/activate

# Install development dependencies
pip install -r requirements-dev.txt

# Run tests with coverage
coverage run -m unittest discover -s tests -p "test_*.py"

# View coverage report in terminal
coverage report

# Generate HTML report
coverage html
# Then open htmlcov/index.html in your browser
```

### End-to-End Tests

The E2E tests workflow:

1. Sets up a MySQL 8.0 database
2. Creates a demo schema with various table types and relationships
3. Runs the populator in analyze-only mode
4. Populates the database with dummy data
5. Verifies that all tables have been populated correctly

To run the E2E tests locally, you'll need a MySQL instance:

```bash
# Create the demo schema
mysql -h localhost -u your_user -p your_database < tests/schemas/demo_schema.sql

# Run the populator
mysql-dummy-populator --host localhost --user your_user --password your_password --database your_database --verify
```

The demo schema includes:

- Tables with primary keys
- Tables with foreign keys
- Tables with circular dependencies
- Many-to-many relationship tables
- Tables with check constraints
- Tables with columns using MySQL reserved keywords
