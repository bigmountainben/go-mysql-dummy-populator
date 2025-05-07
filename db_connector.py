import os
import mysql.connector
from mysql.connector import Error
import logging

class DatabaseConnector:
    """
    Handles database connection and query execution
    """
    def __init__(self, host=None, user=None, password=None, database=None, port=None):
        """
        Initialize database connection parameters from environment variables or passed arguments
        """
        self.host = host or os.getenv('MYSQL_HOST', 'localhost')
        self.user = user or os.getenv('MYSQL_USER', 'root')
        self.password = password or os.getenv('MYSQL_PASSWORD', '')
        self.database = database or os.getenv('MYSQL_DATABASE')
        self.port = port or os.getenv('MYSQL_PORT', '3306')
        self.connection = None
        self.cursor = None

        if not self.database:
            raise ValueError("Database name must be provided either as an argument or as MYSQL_DATABASE environment variable")

    def connect(self):
        """
        Establish connection to the MySQL database
        """
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                port=int(self.port)
            )

            if self.connection.is_connected():
                self.cursor = self.connection.cursor(dictionary=True)
                logging.info(f"Connected to MySQL database: {self.database}")
                return True
        except Error as e:
            logging.error(f"Error connecting to MySQL database: {e}")
            return False

    def disconnect(self):
        """
        Close database connection
        """
        if self.connection and self.connection.is_connected():
            if self.cursor:
                self.cursor.close()
            self.connection.close()
            logging.info("MySQL connection closed")

    def execute_query(self, query, params=None, commit=False):
        """
        Execute a SQL query

        Args:
            query (str): SQL query to execute
            params (tuple, optional): Parameters for the query
            commit (bool, optional): Whether to commit the transaction

        Returns:
            list: Query results or None if error
        """
        try:
            if not self.connection or not self.connection.is_connected():
                self.connect()

            self.cursor.execute(query, params or ())

            if commit:
                self.connection.commit()
                return True

            result = self.cursor.fetchall()
            return result
        except Error as e:
            # Log the error with more details
            error_msg = f"Error executing query: {e}"
            logging.error(error_msg)

            # For syntax errors, log the full query and parameters
            if "1064" in str(e):  # MySQL syntax error code
                formatted_query = query
                if params:
                    try:
                        # Try to format the query with parameters for better debugging
                        if isinstance(params, (list, tuple)):
                            formatted_query = query % tuple(repr(p) if isinstance(p, str) else p for p in params)
                        elif isinstance(params, dict):
                            formatted_query = query % {k: repr(v) if isinstance(v, str) else v for k, v in params.items()}
                    except Exception as format_error:
                        logging.debug(f"Could not format query with params: {format_error}")

                logging.error(f"SQL Syntax Error. Full query: {formatted_query}")

            logging.debug(f"Query: {query}")
            logging.debug(f"Params: {params}")
            return None

    def execute_many(self, query, params_list, commit=True):
        """
        Execute a SQL query with multiple parameter sets

        Args:
            query (str): SQL query to execute
            params_list (list): List of parameter tuples
            commit (bool, optional): Whether to commit the transaction

        Returns:
            bool: Success status
        """
        try:
            if not self.connection or not self.connection.is_connected():
                self.connect()

            self.cursor.executemany(query, params_list)

            if commit:
                self.connection.commit()

            return True
        except Error as e:
            # Log the error with more details
            error_msg = f"Error executing batch query: {e}"
            logging.error(error_msg)

            # For syntax errors, log the full query and parameters
            if "1064" in str(e):  # MySQL syntax error code
                formatted_query = query
                if params_list and len(params_list) > 0:
                    try:
                        # Try to format the query with the first set of parameters for better debugging
                        first_params = params_list[0]
                        if isinstance(first_params, (list, tuple)):
                            formatted_query = query % tuple(repr(p) if isinstance(p, str) else p for p in first_params)
                        elif isinstance(first_params, dict):
                            formatted_query = query % {k: repr(v) if isinstance(v, str) else v for k, v in first_params.items()}
                    except Exception as format_error:
                        logging.debug(f"Could not format query with params: {format_error}")

                logging.error(f"SQL Syntax Error. Full query: {formatted_query}")

            logging.debug(f"Query: {query}")
            logging.debug(f"First params set: {params_list[0] if params_list else None}")
            return False
