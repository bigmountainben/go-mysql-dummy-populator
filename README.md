# MySQL Dummy Data Populator

[![MySQL 8.0+](https://img.shields.io/badge/mysql-8.0+-orange.svg)](https://dev.mysql.com/downloads/)
[![Go 1.16+](https://img.shields.io/badge/go-1.16+-blue.svg)](https://golang.org/dl/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Go tool that populates MySQL databases with realistic dummy data, handling foreign keys, circular dependencies, and many-to-many relationships.

## Project Status

The badges at the top of this README provide at-a-glance information about the project:

- **Go 1.16+**: Indicates Go version compatibility
- **MySQL 8.0+**: Indicates MySQL version compatibility
- **License: MIT**: Shows the project's license
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

- Go 1.16+
- MySQL 8.0+

## Installation

### Option 1: Install using Go

You can install the package directly using Go:

```bash
go install github.com/vitebski/mysql-dummy-populator/cmd/mysql-dummy-populator@latest
```

### Option 2: Install from Source

If you want to install from source:

1. Clone this repository:

   ```bash
   git clone https://github.com/vitebski/mysql-dummy-populator.git
   cd mysql-dummy-populator
   ```

2. Build the application:

   ```bash
   go build -o mysql-dummy-populator ./cmd/mysql-dummy-populator
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
# MySQL connection parameters
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=your_database
MYSQL_PORT=3306

# Application settings
MYSQL_LOG_LEVEL=info  # debug, info, warn, error
MYSQL_RECORDS=10      # Number of records to generate per table
MYSQL_MAX_RETRIES=5   # Maximum number of retries for handling circular dependencies
MYSQL_MIN_RECORDS=1   # Minimum number of records each table should have for verification
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

If you installed the package via Go, you can run the tool directly from the command line:

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
# From the project directory
./mysql-dummy-populator
```

### Available Options

- `--host`, `-H`: MySQL host (default: from MYSQL_HOST env var or .env file)
- `--user`, `-u`: MySQL user (default: from MYSQL_USER env var or .env file)
- `--password`, `-p`: MySQL password (default: from MYSQL_PASSWORD env var or .env file)
- `--database`, `-d`: MySQL database name (default: from MYSQL_DATABASE env var or .env file)
- `--port`, `-P`: MySQL port (default: from MYSQL_PORT env var or .env file, or 3306)
- `--records`, `-r`: Number of records per table (default: from MYSQL_RECORDS env var or .env file, or 10)
- `--max-retries`, `-m`: Maximum number of retries for handling circular dependencies (default: 5)
- `--min-records`, `-n`: Minimum number of records each table should have for verification (default: 1)
- `--log-level`, `-l`: Log level (debug, info, warn, error) (default: from MYSQL_LOG_LEVEL env var or .env file, or info)
- `--env-file`, `-e`: Path to .env file (default: .env)
- `--analyze-only`, `-a`: Only analyze the database schema without populating data
- `--verify`, `-v`: Verify that all tables have been populated with the expected number of records

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
# Run all unit tests
go test ./...

# Run tests with coverage report
go test -cover ./...

# Note: When running tests, you may see warning and error messages like
# "Verification failed: 1 tables have no records". These are expected and
# are part of testing error handling scenarios, not actual test failures.
```

### Code Coverage

To generate a detailed coverage report locally:

```bash
# Generate coverage profile
go test -coverprofile=coverage.out ./...

# View coverage in browser
go tool cover -html=coverage.out

# View coverage in terminal
go tool cover -func=coverage.out
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
