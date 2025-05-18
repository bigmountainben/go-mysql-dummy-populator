package connector

import (
	"os"
	"testing"
)

func TestNewDatabaseConnector(t *testing.T) {
	// Set environment variables for testing
	os.Setenv("MYSQL_HOST", "test-host")
	os.Setenv("MYSQL_USER", "test-user")
	os.Setenv("MYSQL_PASSWORD", "test-password")
	os.Setenv("MYSQL_DATABASE", "test-database")
	os.Setenv("MYSQL_PORT", "3307")

	// Create a new logger for testing
	logger := createTestLogger()

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

// Helper function to create a test logger
func createTestLogger() *MockLogger {
	return &MockLogger{}
}

// MockLogger is a mock implementation of the logrus.Logger
type MockLogger struct{}

func (l *MockLogger) Debugf(format string, args ...interface{})   {}
func (l *MockLogger) Infof(format string, args ...interface{})    {}
func (l *MockLogger) Warningf(format string, args ...interface{}) {}
func (l *MockLogger) Errorf(format string, args ...interface{})   {}
func (l *MockLogger) Debug(args ...interface{})                   {}
func (l *MockLogger) Info(args ...interface{})                    {}
func (l *MockLogger) Warning(args ...interface{})                 {}
func (l *MockLogger) Error(args ...interface{})                   {}
