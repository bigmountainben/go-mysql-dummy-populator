package utils

import (
	"fmt"
	"os"
	"strconv"
	"strings"

	"github.com/joho/godotenv"
	"github.com/sirupsen/logrus"
	"github.com/vitebski/mysql-dummy-populator/internal/analyzer"
	"github.com/vitebski/mysql-dummy-populator/internal/connector"
)

// SetupLogging configures the logging system
func SetupLogging(logLevel string) *logrus.Logger {
	// Create a new logger
	logger := logrus.New()

	// Get log level from environment variable or parameter
	levelStr := logLevel
	if levelStr == "" {
		levelStr = os.Getenv("MYSQL_LOG_LEVEL")
		if levelStr == "" {
			levelStr = "info"
		}
	}

	// Parse log level
	level, err := logrus.ParseLevel(levelStr)
	if err != nil {
		level = logrus.InfoLevel
	}

	// Configure logger
	logger.SetLevel(level)
	logger.SetFormatter(&logrus.TextFormatter{
		FullTimestamp: true,
	})
	logger.SetOutput(os.Stdout)

	logger.Infof("Logging configured with level: %s", level)
	return logger
}

// LoadEnvironmentVariables loads environment variables from .env file
func LoadEnvironmentVariables(envFile string, logger *logrus.Logger) bool {
	// Check if a sample .env file exists but not the actual .env file
	if _, err := os.Stat(envFile); os.IsNotExist(err) {
		sampleEnvFile := envFile + ".sample"
		if _, err := os.Stat(sampleEnvFile); err == nil {
			logger.Infof("No %s file found, but %s exists. Consider copying %s to %s and updating it.",
				envFile, sampleEnvFile, sampleEnvFile, envFile)
		}
	}

	// Load environment variables from .env file if it exists
	if _, err := os.Stat(envFile); err == nil {
		if err := godotenv.Load(envFile); err != nil {
			logger.Warningf("Error loading %s file: %v", envFile, err)
		} else {
			logger.Infof("Loaded environment variables from %s", envFile)
		}
	} else {
		logger.Infof("No %s file found, using existing environment variables", envFile)
	}

	// Check for required environment variables
	requiredVars := []string{"MYSQL_HOST", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DATABASE"}
	var missingVars []string

	for _, v := range requiredVars {
		if os.Getenv(v) == "" {
			missingVars = append(missingVars, v)
		}
	}

	if len(missingVars) > 0 {
		logger.Warningf("Missing required environment variables: %s", strings.Join(missingVars, ", "))
		logger.Info("These can be provided via command line arguments, environment variables, or a .env file")
		return false
	}

	// Log all available MySQL_* environment variables (for debugging)
	if logger.Level == logrus.DebugLevel {
		for _, env := range os.Environ() {
			if strings.HasPrefix(env, "MYSQL_") {
				parts := strings.SplitN(env, "=", 2)
				if len(parts) == 2 {
					// Mask password
					if parts[0] == "MYSQL_PASSWORD" {
						logger.Debugf("%s=********", parts[0])
					} else {
						logger.Debugf("%s=%s", parts[0], parts[1])
					}
				}
			}
		}
	}

	return true
}

// GetEnvInt gets an integer value from environment variable
func GetEnvInt(varName string, defaultValue int) int {
	value := os.Getenv(varName)
	if value == "" {
		return defaultValue
	}

	intValue, err := strconv.Atoi(value)
	if err != nil {
		return defaultValue
	}

	return intValue
}

// PrintSummary prints a summary of the population process
func PrintSummary(tables []string, recordsPerTable int, successfulTables []string, failedTables []string) {
	totalTables := len(tables)
	totalSuccessful := len(successfulTables)
	totalFailed := len(failedTables)
	totalRecords := totalSuccessful * recordsPerTable

	fmt.Println("\n" + strings.Repeat("=", 50))
	fmt.Println("DATABASE POPULATION SUMMARY")
	fmt.Println(strings.Repeat("=", 50))
	fmt.Printf("Total tables processed: %d\n", totalTables)
	fmt.Printf("Successfully populated tables: %d\n", totalSuccessful)
	fmt.Printf("Failed tables: %d\n", totalFailed)
	fmt.Printf("Total records inserted: %d\n", totalRecords)

	if len(failedTables) > 0 {
		fmt.Println("\nFailed tables:")
		for _, table := range failedTables {
			fmt.Printf("  - %s\n", table)
		}
	}

	fmt.Println(strings.Repeat("=", 50))
}

// ValidateConnectionParams validates database connection parameters
func ValidateConnectionParams(host, user, password, database, port string, logger *logrus.Logger) bool {
	if host == "" {
		logger.Error("Database host is required")
		return false
	}

	if user == "" {
		logger.Error("Database user is required")
		return false
	}

	if password == "" { // Empty password is allowed
		logger.Warning("Database password is empty")
	}

	if database == "" {
		logger.Error("Database name is required")
		return false
	}

	if _, err := strconv.Atoi(port); err != nil {
		logger.Errorf("Invalid port number: %s", port)
		return false
	}

	return true
}

// PrintSchemaAnalysis prints a detailed analysis of the database schema
func PrintSchemaAnalysis(schemaAnalyzer *analyzer.SchemaAnalyzer) {
	tables := schemaAnalyzer.Tables
	views := schemaAnalyzer.Views
	foreignKeys := schemaAnalyzer.ForeignKeys
	manyToManyTables := schemaAnalyzer.ManyToManyTables

	// Get table order and circular dependencies
	orderedTables, circularTables := schemaAnalyzer.GetTableInsertionOrder()

	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("DATABASE SCHEMA ANALYSIS REPORT")
	fmt.Println(strings.Repeat("=", 80))

	// Basic statistics
	fmt.Println("\n1. BASIC STATISTICS")
	fmt.Printf("   Total tables: %d\n", len(tables))
	fmt.Printf("   Total views: %d\n", len(views))
	fmt.Printf("   Tables with foreign keys: %d\n", len(foreignKeys))
	fmt.Printf("   Many-to-many relationship tables: %d\n", len(manyToManyTables))
	fmt.Printf("   Tables in circular dependencies: %d\n", len(circularTables))

	// Table categories
	var standaloneTables []string
	var dependentTables []string

	for _, table := range tables {
		if _, hasFKs := foreignKeys[table]; !hasFKs && !circularTables[table] {
			standaloneTables = append(standaloneTables, table)
		} else if !circularTables[table] && !manyToManyTables[table] {
			dependentTables = append(dependentTables, table)
		}
	}

	fmt.Println("\n2. TABLE CATEGORIES")
	fmt.Printf("   Standalone tables (no foreign keys): %d\n", len(standaloneTables))
	fmt.Printf("   Dependent tables (with foreign keys, no circular deps): %d\n", len(dependentTables))
	fmt.Printf("   Many-to-many tables: %d\n", len(manyToManyTables))
	fmt.Printf("   Tables in circular dependencies: %d\n", len(circularTables))

	// Circular dependencies
	if len(circularTables) > 0 {
		fmt.Println("\n3. CIRCULAR DEPENDENCIES")
		fmt.Printf("   Total tables involved: %d\n", len(circularTables))

		// Print tables involved in circular dependencies
		var circularTablesList []string
		for table := range circularTables {
			circularTablesList = append(circularTablesList, table)
		}
		fmt.Printf("   Tables involved: %s\n", strings.Join(circularTablesList, ", "))

		// Print direct circular dependencies
		fmt.Println("\n   Direct circular dependencies:")
		for _, dep := range schemaAnalyzer.DirectCircularDeps {
			if len(dep) >= 2 {
				fmt.Printf("     %s <-> %s\n", dep[0], dep[1])
			}
		}
	}

	// Many-to-many tables
	if len(manyToManyTables) > 0 {
		fmt.Println("\n4. MANY-TO-MANY RELATIONSHIP TABLES")
		fmt.Printf("   Total detected: %d\n", len(manyToManyTables))

		// Print many-to-many tables
		var manyToManyTablesList []string
		for table := range manyToManyTables {
			manyToManyTablesList = append(manyToManyTablesList, table)
		}
		fmt.Printf("   Tables: %s\n", strings.Join(manyToManyTablesList, ", "))
	}

	// Table insertion order
	fmt.Println("\n5. RECOMMENDED TABLE INSERTION ORDER")
	for i, table := range orderedTables {
		category := "Standalone"
		if manyToManyTables[table] {
			category = "Many-to-Many"
		} else if circularTables[table] {
			category = "Circular"
		} else if _, hasFKs := foreignKeys[table]; hasFKs {
			category = "Dependent"
		}
		fmt.Printf("   %3d. %s (%s)\n", i+1, table, category)
	}

	fmt.Println("\n" + strings.Repeat("=", 80))
}

// VerifyTablePopulation verifies that all tables have at least the minimum number of records
func VerifyTablePopulation(db *connector.DatabaseConnector, tables []string, minRecords int, logger *logrus.Logger) (bool, []string, map[string]int) {
	logger.Infof("Verifying that all tables have at least %d record(s)...", minRecords)

	emptyTables := []string{}
	partiallyPopulatedTables := make(map[string]int)

	for _, table := range tables {
		query := fmt.Sprintf("SELECT COUNT(*) as count FROM %s", table)
		result, err := db.ExecuteQuery(query)
		if err != nil {
			logger.Warningf("Could not verify record count for table: %s", table)
			emptyTables = append(emptyTables, table)
			continue
		}

		if len(result) == 0 {
			logger.Warningf("No result returned for count query on table: %s", table)
			emptyTables = append(emptyTables, table)
			continue
		}

		count, ok := result[0]["count"].(int64)
		if !ok {
			// Try to convert to int64
			countStr := fmt.Sprintf("%v", result[0]["count"])
			countInt, err := strconv.ParseInt(countStr, 10, 64)
			if err != nil {
				logger.Warningf("Could not parse count for table %s: %v", table, err)
				emptyTables = append(emptyTables, table)
				continue
			}
			count = countInt
		}

		if count == 0 {
			logger.Warningf("Table %s has no records", table)
			emptyTables = append(emptyTables, table)
		} else if count < int64(minRecords) {
			logger.Warningf("Table %s has only %d/%d expected records", table, count, minRecords)
			partiallyPopulatedTables[table] = int(count)
		}
	}

	success := len(emptyTables) == 0 && len(partiallyPopulatedTables) == 0

	if success {
		logger.Info("Verification successful: All tables have at least the minimum number of records")
	} else {
		if len(emptyTables) > 0 {
			logger.Errorf("Verification failed: %d tables have no records", len(emptyTables))
		}
		if len(partiallyPopulatedTables) > 0 {
			logger.Errorf("Verification failed: %d tables are partially populated", len(partiallyPopulatedTables))
		}
	}

	return success, emptyTables, partiallyPopulatedTables
}

// PrintVerificationResults prints the results of the table population verification
func PrintVerificationResults(emptyTables []string, partiallyPopulatedTables map[string]int, minRecords int) {
	fmt.Println("\n" + strings.Repeat("=", 50))
	fmt.Println("TABLE POPULATION VERIFICATION RESULTS")
	fmt.Println(strings.Repeat("=", 50))

	if len(emptyTables) == 0 && len(partiallyPopulatedTables) == 0 {
		fmt.Printf("✅ All tables have at least %d record(s)\n", minRecords)
		fmt.Println(strings.Repeat("=", 50))
		return
	}

	if len(emptyTables) > 0 {
		fmt.Printf("❌ %d tables have no records:\n", len(emptyTables))
		for _, table := range emptyTables {
			fmt.Printf("  - %s\n", table)
		}
		fmt.Println()
	}

	if len(partiallyPopulatedTables) > 0 {
		fmt.Printf("⚠️  %d tables are partially populated:\n", len(partiallyPopulatedTables))
		for table, count := range partiallyPopulatedTables {
			fmt.Printf("  - %s: %d/%d records\n", table, count, minRecords)
		}
		fmt.Println()
	}

	fmt.Println(strings.Repeat("=", 50))
}
