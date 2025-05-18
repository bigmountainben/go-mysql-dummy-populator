package utils

import (
	"os"
	"testing"

	"github.com/sirupsen/logrus"
)

func TestSetupLogging(t *testing.T) {
	// Test with default log level
	logger := SetupLogging("")
	if logger == nil {
		t.Error("Expected logger to be created, got nil")
	}

	// Test with specific log level
	logger = SetupLogging("debug")
	if logger.Level != logrus.DebugLevel {
		t.Errorf("Expected log level to be debug, got %s", logger.Level)
	}

	logger = SetupLogging("info")
	if logger.Level != logrus.InfoLevel {
		t.Errorf("Expected log level to be info, got %s", logger.Level)
	}

	logger = SetupLogging("warn")
	if logger.Level != logrus.WarnLevel {
		t.Errorf("Expected log level to be warn, got %s", logger.Level)
	}

	logger = SetupLogging("error")
	if logger.Level != logrus.ErrorLevel {
		t.Errorf("Expected log level to be error, got %s", logger.Level)
	}

	// Test with invalid log level (should default to info)
	logger = SetupLogging("invalid")
	if logger.Level != logrus.InfoLevel {
		t.Errorf("Expected log level to be info for invalid input, got %s", logger.Level)
	}
}

func TestGetEnvInt(t *testing.T) {
	// Test with environment variable set
	os.Setenv("TEST_ENV_INT", "42")
	value := GetEnvInt("TEST_ENV_INT", 10)
	if value != 42 {
		t.Errorf("Expected value to be 42, got %d", value)
	}

	// Test with environment variable not set
	os.Unsetenv("TEST_ENV_INT")
	value = GetEnvInt("TEST_ENV_INT", 10)
	if value != 10 {
		t.Errorf("Expected value to be 10 (default), got %d", value)
	}

	// Test with invalid integer
	os.Setenv("TEST_ENV_INT", "not-an-int")
	value = GetEnvInt("TEST_ENV_INT", 10)
	if value != 10 {
		t.Errorf("Expected value to be 10 (default) for invalid input, got %d", value)
	}
}

func TestValidateConnectionParams(t *testing.T) {
	logger := logrus.New()
	logger.SetLevel(logrus.FatalLevel) // Suppress log output during tests

	// Test with valid parameters
	valid := ValidateConnectionParams("localhost", "user", "password", "database", "3306", logger)
	if !valid {
		t.Error("Expected validation to pass with valid parameters")
	}

	// Test with missing host
	valid = ValidateConnectionParams("", "user", "password", "database", "3306", logger)
	if valid {
		t.Error("Expected validation to fail with missing host")
	}

	// Test with missing user
	valid = ValidateConnectionParams("localhost", "", "password", "database", "3306", logger)
	if valid {
		t.Error("Expected validation to fail with missing user")
	}

	// Test with missing database
	valid = ValidateConnectionParams("localhost", "user", "password", "", "3306", logger)
	if valid {
		t.Error("Expected validation to fail with missing database")
	}

	// Test with invalid port
	valid = ValidateConnectionParams("localhost", "user", "password", "database", "not-a-port", logger)
	if valid {
		t.Error("Expected validation to fail with invalid port")
	}

	// Empty password is allowed
	valid = ValidateConnectionParams("localhost", "user", "", "database", "3306", logger)
	if !valid {
		t.Error("Expected validation to pass with empty password")
	}
}
