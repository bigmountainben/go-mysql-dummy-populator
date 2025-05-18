package connector

import (
	"os"
	"testing"

	"github.com/DATA-DOG/go-sqlmock"
	"github.com/sirupsen/logrus"
)

func TestNewDatabaseConnector(t *testing.T) {
	// Set environment variables for testing
	os.Setenv("MYSQL_HOST", "test-host")
	os.Setenv("MYSQL_USER", "test-user")
	os.Setenv("MYSQL_PASSWORD", "test-password")
	os.Setenv("MYSQL_DATABASE", "test-database")
	os.Setenv("MYSQL_PORT", "3307")

	// Create a new logger for testing
	logger := logrus.New()
	logger.SetLevel(logrus.FatalLevel) // Suppress log output during tests

	// Create a new database connector
	db := NewDatabaseConnector("", "", "", "", "", logger)

	// Check that environment variables were used
	if db.Host != "test-host" {
		t.Errorf("Expected host to be 'test-host', got '%s'", db.Host)
	}
	if db.User != "test-user" {
		t.Errorf("Expected user to be 'test-user', got '%s'", db.User)
	}
	if db.Password != "test-password" {
		t.Errorf("Expected password to be 'test-password', got '%s'", db.Password)
	}
	if db.Database != "test-database" {
		t.Errorf("Expected database to be 'test-database', got '%s'", db.Database)
	}
	if db.Port != "3307" {
		t.Errorf("Expected port to be '3307', got '%s'", db.Port)
	}

	// Test with explicit parameters
	db = NewDatabaseConnector("explicit-host", "explicit-user", "explicit-password", "explicit-database", "3308", logger)

	// Check that explicit parameters were used
	if db.Host != "explicit-host" {
		t.Errorf("Expected host to be 'explicit-host', got '%s'", db.Host)
	}
	if db.User != "explicit-user" {
		t.Errorf("Expected user to be 'explicit-user', got '%s'", db.User)
	}
	if db.Password != "explicit-password" {
		t.Errorf("Expected password to be 'explicit-password', got '%s'", db.Password)
	}
	if db.Database != "explicit-database" {
		t.Errorf("Expected database to be 'explicit-database', got '%s'", db.Database)
	}
	if db.Port != "3308" {
		t.Errorf("Expected port to be '3308', got '%s'", db.Port)
	}
}

func TestExecuteQuery(t *testing.T) {
	// Create a mock database
	db, mock, err := sqlmock.New()
	if err != nil {
		t.Fatalf("Error creating mock database: %v", err)
	}
	defer db.Close()

	// Create a logger
	logger := logrus.New()
	logger.SetLevel(logrus.FatalLevel) // Suppress log output during tests

	// Create a database connector with the mock database
	connector := &DatabaseConnector{
		Host:     "localhost",
		User:     "user",
		Password: "password",
		Database: "database",
		Port:     "3306",
		DB:       db,
		Logger:   logger,
	}

	// Set up expected query and result
	rows := sqlmock.NewRows([]string{"id", "name"}).AddRow(1, "test")
	mock.ExpectQuery("SELECT \\* FROM test").WillReturnRows(rows)

	// Execute the query
	result, err := connector.ExecuteQuery("SELECT * FROM test")
	if err != nil {
		t.Errorf("Error executing query: %v", err)
	}

	// Check the result
	if len(result) != 1 {
		t.Errorf("Expected 1 row, got %d", len(result))
	}
	if result[0]["id"] != int64(1) {
		t.Errorf("Expected id to be 1, got %v", result[0]["id"])
	}
	if result[0]["name"] != "test" {
		t.Errorf("Expected name to be 'test', got %v", result[0]["name"])
	}

	// Verify that all expectations were met
	if err := mock.ExpectationsWereMet(); err != nil {
		t.Errorf("Unfulfilled expectations: %v", err)
	}
}

func TestExecuteStatement(t *testing.T) {
	// Create a mock database
	db, mock, err := sqlmock.New()
	if err != nil {
		t.Fatalf("Error creating mock database: %v", err)
	}
	defer db.Close()

	// Create a logger
	logger := logrus.New()
	logger.SetLevel(logrus.FatalLevel) // Suppress log output during tests

	// Create a database connector with the mock database
	connector := &DatabaseConnector{
		Host:     "localhost",
		User:     "user",
		Password: "password",
		Database: "database",
		Port:     "3306",
		DB:       db,
		Logger:   logger,
	}

	// Set up expected statement and result
	mock.ExpectExec("INSERT INTO test").WithArgs(1, "test").WillReturnResult(sqlmock.NewResult(1, 1))

	// Execute the statement
	affected, err := connector.ExecuteStatement("INSERT INTO test", 1, "test")
	if err != nil {
		t.Errorf("Error executing statement: %v", err)
	}

	// Check the result
	if affected != 1 {
		t.Errorf("Expected 1 affected row, got %d", affected)
	}

	// Verify that all expectations were met
	if err := mock.ExpectationsWereMet(); err != nil {
		t.Errorf("Unfulfilled expectations: %v", err)
	}
}

func TestExecuteMany(t *testing.T) {
	// Create a mock database
	db, mock, err := sqlmock.New()
	if err != nil {
		t.Fatalf("Error creating mock database: %v", err)
	}
	defer db.Close()

	// Create a logger
	logger := logrus.New()
	logger.SetLevel(logrus.FatalLevel) // Suppress log output during tests

	// Create a database connector with the mock database
	connector := &DatabaseConnector{
		Host:     "localhost",
		User:     "user",
		Password: "password",
		Database: "database",
		Port:     "3306",
		DB:       db,
		Logger:   logger,
	}

	// Set up expected transaction and statements
	mock.ExpectBegin()
	stmt := mock.ExpectPrepare("INSERT INTO test")
	stmt.ExpectExec().WithArgs(1, "test1").WillReturnResult(sqlmock.NewResult(1, 1))
	stmt.ExpectExec().WithArgs(2, "test2").WillReturnResult(sqlmock.NewResult(2, 1))
	mock.ExpectCommit()

	// Execute the batch statement
	paramsList := [][]interface{}{
		{1, "test1"},
		{2, "test2"},
	}
	affected, err := connector.ExecuteMany("INSERT INTO test", paramsList)
	if err != nil {
		t.Errorf("Error executing batch statement: %v", err)
	}

	// Check the result
	if affected != 2 {
		t.Errorf("Expected 2 affected rows, got %d", affected)
	}

	// Verify that all expectations were met
	if err := mock.ExpectationsWereMet(); err != nil {
		t.Errorf("Unfulfilled expectations: %v", err)
	}
}

func TestConnect(t *testing.T) {
	// Create a logger
	logger := logrus.New()
	logger.SetLevel(logrus.FatalLevel) // Suppress log output during tests

	// Create a database connector
	connector := NewDatabaseConnector("localhost", "user", "password", "", "3306", logger)

	// Test missing database name
	err := connector.Connect()
	if err == nil {
		t.Error("Expected error for missing database name, got nil")
	}

	// Restore database name
	connector.Database = "database"

	// We can't fully test the Connect method without a real database,
	// but we can at least verify it doesn't panic
	// Note: This will fail because we can't mock sql.Open easily
	// This is just to demonstrate the approach
	// err = connector.Connect()
	// if err == nil {
	// 	t.Error("Expected error for connection failure, got nil")
	// }
}
