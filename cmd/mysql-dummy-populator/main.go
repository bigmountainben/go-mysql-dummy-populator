package main

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"
	"github.com/vitebski/mysql-dummy-populator/internal/analyzer"
	"github.com/vitebski/mysql-dummy-populator/internal/connector"
	"github.com/vitebski/mysql-dummy-populator/internal/generator"
	"github.com/vitebski/mysql-dummy-populator/internal/populator"
	"github.com/vitebski/mysql-dummy-populator/internal/utils"
)

func main() {
	var (
		host        string
		user        string
		password    string
		database    string
		port        string
		records     int
		maxRetries  int
		minRecords  int
		envFile     string
		logLevel    string
		analyzeOnly bool
		verify      bool
	)

	rootCmd := &cobra.Command{
		Use:   "mysql-dummy-populator",
		Short: "A tool to populate MySQL databases with realistic dummy data",
		Long: `MySQL Dummy Data Populator

A Go tool that populates MySQL databases with realistic dummy data,
handling foreign keys, circular dependencies, and many-to-many relationships.`,
		Run: func(cmd *cobra.Command, args []string) {
			// Setup logging
			logger := utils.SetupLogging(logLevel)

			// Load environment variables
			utils.LoadEnvironmentVariables(envFile, logger)

			// Get connection parameters from environment if not provided
			if host == "" {
				host = os.Getenv("MYSQL_HOST")
			}
			if user == "" {
				user = os.Getenv("MYSQL_USER")
			}
			if password == "" {
				password = os.Getenv("MYSQL_PASSWORD")
			}
			if database == "" {
				database = os.Getenv("MYSQL_DATABASE")
			}
			if port == "" {
				port = os.Getenv("MYSQL_PORT")
				if port == "" {
					port = "3306"
				}
			}

			// Validate connection parameters
			if !utils.ValidateConnectionParams(host, user, password, database, port, logger) {
				os.Exit(1)
			}

			// Create database connector
			db := connector.NewDatabaseConnector(host, user, password, database, port, logger)
			if err := db.Connect(); err != nil {
				logger.Errorf("Failed to connect to database: %v", err)
				os.Exit(1)
			}
			defer db.Disconnect()

			// Create schema analyzer
			schemaAnalyzer := analyzer.NewSchemaAnalyzer(db, logger)
			if err := schemaAnalyzer.AnalyzeSchema(); err != nil {
				logger.Errorf("Failed to analyze schema: %v", err)
				os.Exit(1)
			}

			// Print schema analysis
			utils.PrintSchemaAnalysis(schemaAnalyzer)

			// If analyze-only mode, exit here
			if analyzeOnly {
				logger.Info("Analyze-only mode, exiting without populating data")
				return
			}

			// Get tables
			tables := schemaAnalyzer.Tables
			if len(tables) == 0 {
				logger.Error("No tables found in database")
				os.Exit(1)
			}

			// Create data generator
			dataGenerator := generator.NewDataGenerator(schemaAnalyzer, logger)

			// Create database populator
			dbPopulator := populator.NewDatabasePopulator(
				db,
				schemaAnalyzer,
				dataGenerator,
				records,
				maxRetries,
				logger,
			)

			// Populate database
			logger.Info("Starting database population...")
			success := dbPopulator.PopulateDatabase()

			// Get successful and failed tables
			var successfulTables []string
			var failedTables []string
			for _, table := range tables {
				if dbPopulator.FailedTables[table] {
					failedTables = append(failedTables, table)
				} else {
					successfulTables = append(successfulTables, table)
				}
			}

			// Print summary
			utils.PrintSummary(tables, records, successfulTables, failedTables)

			// Verify table population if requested
			verificationSuccess := true
			if verify {
				var emptyTables []string
				var partiallyPopulatedTables map[string]int
				verificationSuccess, emptyTables, partiallyPopulatedTables = utils.VerifyTablePopulation(
					db, tables, minRecords, logger,
				)
				utils.PrintVerificationResults(emptyTables, partiallyPopulatedTables, minRecords)
			}

			// Return appropriate exit code
			if !success || (verify && !verificationSuccess) {
				os.Exit(1)
			}
		},
	}

	// Define flags
	rootCmd.Flags().StringVarP(&host, "host", "H", "", "MySQL host (default: localhost)")
	rootCmd.Flags().StringVarP(&user, "user", "u", "", "MySQL user (default: root)")
	rootCmd.Flags().StringVarP(&password, "password", "p", "", "MySQL password")
	rootCmd.Flags().StringVarP(&database, "database", "d", "", "MySQL database name")
	rootCmd.Flags().StringVarP(&port, "port", "P", "", "MySQL port (default: 3306)")
	rootCmd.Flags().IntVarP(&records, "records", "r", 10, "Number of records to generate per table")
	rootCmd.Flags().IntVarP(&maxRetries, "max-retries", "m", 5, "Maximum number of retries for handling circular dependencies")
	rootCmd.Flags().IntVarP(&minRecords, "min-records", "n", 1, "Minimum number of records each table should have for verification")
	rootCmd.Flags().StringVarP(&envFile, "env-file", "e", ".env", "Path to .env file")
	rootCmd.Flags().StringVarP(&logLevel, "log-level", "l", "", "Log level (debug, info, warn, error)")
	rootCmd.Flags().BoolVarP(&analyzeOnly, "analyze-only", "a", false, "Only analyze the database schema without populating data")
	rootCmd.Flags().BoolVarP(&verify, "verify", "v", false, "Verify that all tables have been populated with the expected number of records")

	// Execute
	if err := rootCmd.Execute(); err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
}
