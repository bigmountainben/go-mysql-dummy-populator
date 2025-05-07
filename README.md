# MySQL Dummy Data Populator

A Python tool that populates MySQL databases with realistic dummy data, handling foreign keys, circular dependencies, and many-to-many relationships.

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

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/mysql-dummy-populator.git
   cd mysql-dummy-populator
   ```

2. Install virtualenv if you don't have it already:
   ```bash
   pip install virtualenv
   ```

3. Create and activate a virtual environment:

   **For Unix/macOS:**
   ```bash
   # Create a virtual environment
   virtualenv venv

   # Activate the virtual environment
   source venv/bin/activate
   ```

   **For Windows:**
   ```bash
   # Create a virtual environment
   virtualenv venv

   # Activate the virtual environment
   venv\Scripts\activate
   ```

4. Install the required dependencies:
   ```bash
   # Make sure you're in the virtual environment (you should see (venv) in your terminal)
   pip install -r requirements.txt
   ```

5. Create a `.env` file with your MySQL connection details:
   ```bash
   # Copy the sample file
   cp .env.sample .env

   # Edit the .env file with your database details
   nano .env  # or use your preferred editor
   ```

6. When you're done using the tool, you can deactivate the virtual environment:
   ```bash
   deactivate
   ```

## Configuration

The tool can be configured in three ways, with the following priority order (highest to lowest):

1. **Command-line arguments**
2. **Environment variables**
3. **.env file**

### .env File Configuration

The tool automatically looks for a `.env` file in the current directory. You can use the provided `.env.sample` as a template:

```
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

Make sure your virtual environment is activated before running the tool:

```bash
# For Unix/macOS
source venv/bin/activate

# For Windows
venv\Scripts\activate
```

You should see `(venv)` at the beginning of your command prompt when the virtual environment is active.

Run the tool with default settings (using configuration from `.env` file or environment variables):

```bash
python main.py
```

Or specify parameters directly:

```bash
python main.py --host localhost --user root --password your_password --database your_database --records 20
```

You can also specify a custom `.env` file:

```bash
python main.py --env-file /path/to/custom/.env
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
python main.py --analyze-only
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
