package connector

import (
	"database/sql"
	"fmt"
	"os"
	"strconv"

	_ "github.com/go-sql-driver/mysql"
	"github.com/sirupsen/logrus"
)

// DatabaseConnector handles database connection and query execution
type DatabaseConnector struct {
	Host     string
	User     string
	Password string
	Database string
	Port     string
	DB       *sql.DB
	Logger   *logrus.Logger
}

// NewDatabaseConnector creates a new database connector
func NewDatabaseConnector(host, user, password, database, port string, logger *logrus.Logger) *DatabaseConnector {
	if host == "" {
		host = getEnvOrDefault("MYSQL_HOST", "localhost")
	}
	if user == "" {
		user = getEnvOrDefault("MYSQL_USER", "root")
	}
	if password == "" {
		password = getEnvOrDefault("MYSQL_PASSWORD", "")
	}
	if database == "" {
		database = getEnvOrDefault("MYSQL_DATABASE", "")
	}
	if port == "" {
		port = getEnvOrDefault("MYSQL_PORT", "3306")
	}

	return &DatabaseConnector{
		Host:     host,
		User:     user,
		Password: password,
		Database: database,
		Port:     port,
		Logger:   logger,
	}
}

// Connect establishes a connection to the MySQL database
func (dc *DatabaseConnector) Connect() error {
	if dc.Database == "" {
		return fmt.Errorf("database name must be provided either as an argument or as MYSQL_DATABASE environment variable")
	}

	dsn := fmt.Sprintf("%s:%s@tcp(%s:%s)/%s?parseTime=true", dc.User, dc.Password, dc.Host, dc.Port, dc.Database)
	db, err := sql.Open("mysql", dsn)
	if err != nil {
		dc.Logger.Errorf("Error connecting to MySQL database: %v", err)
		return err
	}

	// Test the connection
	err = db.Ping()
	if err != nil {
		dc.Logger.Errorf("Error pinging MySQL database: %v", err)
		return err
	}

	dc.DB = db
	dc.Logger.Infof("Connected to MySQL database: %s", dc.Database)
	return nil
}

// Disconnect closes the database connection
func (dc *DatabaseConnector) Disconnect() {
	if dc.DB != nil {
		err := dc.DB.Close()
		if err != nil {
			dc.Logger.Errorf("Error closing database connection: %v", err)
		} else {
			dc.Logger.Info("MySQL connection closed")
		}
	}
}

// ExecuteQuery executes a SQL query and returns the results
func (dc *DatabaseConnector) ExecuteQuery(query string, params ...interface{}) ([]map[string]interface{}, error) {
	if dc.DB == nil {
		if err := dc.Connect(); err != nil {
			return nil, err
		}
	}

	rows, err := dc.DB.Query(query, params...)
	if err != nil {
		dc.Logger.Errorf("Error executing query: %v", err)
		return nil, err
	}
	defer rows.Close()

	columns, err := rows.Columns()
	if err != nil {
		dc.Logger.Errorf("Error getting columns: %v", err)
		return nil, err
	}

	var results []map[string]interface{}

	for rows.Next() {
		// Create a slice of interface{} to hold the values
		values := make([]interface{}, len(columns))
		// Create a slice of pointers to the values
		valuePtrs := make([]interface{}, len(columns))
		for i := range columns {
			valuePtrs[i] = &values[i]
		}

		// Scan the result into the pointers
		if err := rows.Scan(valuePtrs...); err != nil {
			dc.Logger.Errorf("Error scanning row: %v", err)
			return nil, err
		}

		// Create a map for this row
		row := make(map[string]interface{})
		for i, col := range columns {
			val := values[i]
			// Handle null values
			if val == nil {
				row[col] = nil
			} else {
				// Convert []byte to string for text fields
				if b, ok := val.([]byte); ok {
					row[col] = string(b)
				} else {
					row[col] = val
				}
			}
		}

		results = append(results, row)
	}

	if err := rows.Err(); err != nil {
		dc.Logger.Errorf("Error iterating rows: %v", err)
		return nil, err
	}

	return results, nil
}

// ExecuteStatement executes a SQL statement and returns the number of affected rows
func (dc *DatabaseConnector) ExecuteStatement(query string, params ...interface{}) (int64, error) {
	if dc.DB == nil {
		if err := dc.Connect(); err != nil {
			return 0, err
		}
	}

	result, err := dc.DB.Exec(query, params...)
	if err != nil {
		dc.Logger.Errorf("Error executing statement: %v", err)
		return 0, err
	}

	affected, err := result.RowsAffected()
	if err != nil {
		dc.Logger.Errorf("Error getting affected rows: %v", err)
		return 0, err
	}

	return affected, nil
}

// ExecuteMany executes a SQL statement with multiple parameter sets
func (dc *DatabaseConnector) ExecuteMany(query string, paramsList [][]interface{}) (int64, error) {
	if dc.DB == nil {
		if err := dc.Connect(); err != nil {
			return 0, err
		}
	}

	// Start a transaction
	tx, err := dc.DB.Begin()
	if err != nil {
		dc.Logger.Errorf("Error starting transaction: %v", err)
		return 0, err
	}

	// Prepare the statement
	stmt, err := tx.Prepare(query)
	if err != nil {
		dc.Logger.Errorf("Error preparing statement: %v", err)
		tx.Rollback()
		return 0, err
	}
	defer stmt.Close()

	var totalAffected int64

	// Execute the statement for each set of parameters
	for _, params := range paramsList {
		result, err := stmt.Exec(params...)
		if err != nil {
			dc.Logger.Errorf("Error executing batch statement: %v", err)
			tx.Rollback()
			return 0, err
		}

		affected, err := result.RowsAffected()
		if err != nil {
			dc.Logger.Errorf("Error getting affected rows: %v", err)
			tx.Rollback()
			return 0, err
		}

		totalAffected += affected
	}

	// Commit the transaction
	if err := tx.Commit(); err != nil {
		dc.Logger.Errorf("Error committing transaction: %v", err)
		tx.Rollback()
		return 0, err
	}

	return totalAffected, nil
}

// getEnvOrDefault gets an environment variable or returns a default value
func getEnvOrDefault(key, defaultValue string) string {
	if value, exists := os.LookupEnv(key); exists {
		return value
	}
	return defaultValue
}

// GetEnvInt gets an integer value from an environment variable
func GetEnvInt(key string, defaultValue int) int {
	if value, exists := os.LookupEnv(key); exists {
		if intValue, err := strconv.Atoi(value); err == nil {
			return intValue
		}
	}
	return defaultValue
}
