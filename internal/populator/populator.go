package populator

import (
	"fmt"
	"strings"
	"time"

	"github.com/sirupsen/logrus"
	"github.com/vitebski/mysql-dummy-populator/internal/analyzer"
	"github.com/vitebski/mysql-dummy-populator/internal/connector"
	"github.com/vitebski/mysql-dummy-populator/internal/generator"
	"github.com/vitebski/mysql-dummy-populator/pkg/models"
)

// DatabasePopulator populates database tables with fake data
type DatabasePopulator struct {
	DB             *connector.DatabaseConnector
	SchemaAnalyzer *analyzer.SchemaAnalyzer
	DataGenerator  *generator.DataGenerator
	NumRecords     int
	MaxRetries     int
	InsertedData   map[string][]map[string]interface{}
	FailedTables   map[string]bool
	Logger         *logrus.Logger
}

// NewDatabasePopulator creates a new database populator
func NewDatabasePopulator(
	db *connector.DatabaseConnector,
	schemaAnalyzer *analyzer.SchemaAnalyzer,
	dataGenerator *generator.DataGenerator,
	numRecords int,
	maxRetries int,
	logger *logrus.Logger,
) *DatabasePopulator {
	return &DatabasePopulator{
		DB:             db,
		SchemaAnalyzer: schemaAnalyzer,
		DataGenerator:  dataGenerator,
		NumRecords:     numRecords,
		MaxRetries:     maxRetries,
		InsertedData:   make(map[string][]map[string]interface{}),
		FailedTables:   make(map[string]bool),
		Logger:         logger,
	}
}

// PopulateDatabase populates the database with fake data
func (dp *DatabasePopulator) PopulateDatabase() bool {
	// Get table insertion order
	orderedTables, circularTables := dp.SchemaAnalyzer.GetTableInsertionOrder()

	// Track overall success
	success := true

	// Populate tables in order
	for _, table := range orderedTables {
		tableSuccess := false

		// Check if this table is part of a circular dependency
		isCircular := circularTables[table]

		if isCircular {
			// Handle circular dependency with special approach
			tableSuccess = dp.populateCircularTable(table)
		} else {
			// Normal table population
			tableSuccess = dp.populateTable(table)
		}

		if !tableSuccess {
			dp.FailedTables[table] = true
			success = false
		}
	}

	return success
}

// populateTable populates a single table with fake data
func (dp *DatabasePopulator) populateTable(table string) bool {
	dp.Logger.Infof("Populating table: %s", table)

	// Get columns for this table
	columns := dp.SchemaAnalyzer.TableColumns[table]
	if len(columns) == 0 {
		dp.Logger.Errorf("No columns found for table: %s", table)
		return false
	}

	// Check if this is a many-to-many table
	isManyToMany := dp.SchemaAnalyzer.ManyToManyTables[table]

	// Get foreign keys for this table
	foreignKeys := dp.SchemaAnalyzer.ForeignKeys[table]

	// Prepare column names and placeholders for the INSERT statement
	var columnNames []string
	var placeholders []string
	var columnObjects []models.Column

	for _, column := range columns {
		// Skip auto-increment columns
		if strings.Contains(strings.ToLower(column.Extra), "auto_increment") {
			continue
		}

		columnNames = append(columnNames, column.Name)
		placeholders = append(placeholders, "?")
		columnObjects = append(columnObjects, column)
	}

	if len(columnNames) == 0 {
		dp.Logger.Warningf("No insertable columns found for table: %s", table)
		return true // Consider this a success since there's nothing to insert
	}

	// Prepare the INSERT statement
	insertSQL := fmt.Sprintf(
		"INSERT INTO %s (%s) VALUES (%s)",
		table,
		strings.Join(columnNames, ", "),
		strings.Join(placeholders, ", "),
	)

	// Determine how many records to insert
	numRecords := dp.NumRecords
	if isManyToMany {
		// For many-to-many tables, calculate based on related tables
		numRecords = dp.calculateManyToManyRecords(table, foreignKeys)
	}

	// Generate and insert data
	var paramsList [][]interface{}
	var insertedRecords []map[string]interface{}

	for i := 0; i < numRecords; i++ {
		// Generate a record
		record, params := dp.generateRecord(table, columnNames, columnObjects, foreignKeys)
		
		if params != nil {
			paramsList = append(paramsList, params)
			insertedRecords = append(insertedRecords, record)
		}

		// Insert in batches of 100 records
		if len(paramsList) >= 100 || (i == numRecords-1 && len(paramsList) > 0) {
			_, err := dp.DB.ExecuteMany(insertSQL, paramsList)
			if err != nil {
				dp.Logger.Errorf("Error inserting data into table %s: %v", table, err)
				return false
			}

			// Store inserted data for reference
			dp.InsertedData[table] = append(dp.InsertedData[table], insertedRecords...)

			// Reset for next batch
			paramsList = nil
			insertedRecords = nil
		}
	}

	dp.Logger.Infof("Successfully populated table %s with %d records", table, numRecords)
	return true
}

// populateCircularTable populates a table involved in circular dependencies
func (dp *DatabasePopulator) populateCircularTable(table string) bool {
	dp.Logger.Infof("Populating circular dependency table: %s", table)

	// Get columns for this table
	columns := dp.SchemaAnalyzer.TableColumns[table]
	if len(columns) == 0 {
		dp.Logger.Errorf("No columns found for table: %s", table)
		return false
	}

	// Get foreign keys for this table
	foreignKeys := dp.SchemaAnalyzer.ForeignKeys[table]

	// Identify circular foreign keys
	var circularFKs []models.ForeignKey
	var nonCircularFKs []models.ForeignKey
	circularTables, _ := dp.SchemaAnalyzer.GetTableInsertionOrder()
	circularTablesMap := make(map[string]bool)
	for _, t := range circularTables {
		circularTablesMap[t] = true
	}

	for _, fk := range foreignKeys {
		if circularTablesMap[fk.ReferencedTable] {
			circularFKs = append(circularFKs, fk)
		} else {
			nonCircularFKs = append(nonCircularFKs, fk)
		}
	}

	// Prepare column names and placeholders for the INSERT statement
	var columnNames []string
	var placeholders []string
	var columnObjects []models.Column

	for _, column := range columns {
		// Skip auto-increment columns
		if strings.Contains(strings.ToLower(column.Extra), "auto_increment") {
			continue
		}

		columnNames = append(columnNames, column.Name)
		placeholders = append(placeholders, "?")
		columnObjects = append(columnObjects, column)
	}

	if len(columnNames) == 0 {
		dp.Logger.Warningf("No insertable columns found for table: %s", table)
		return true // Consider this a success since there's nothing to insert
	}

	// Prepare the INSERT statement
	insertSQL := fmt.Sprintf(
		"INSERT INTO %s (%s) VALUES (%s)",
		table,
		strings.Join(columnNames, ", "),
		strings.Join(placeholders, ", "),
	)

	// First pass: Insert records with NULL for circular foreign keys
	dp.Logger.Infof("First pass: Inserting records with NULL for circular foreign keys")
	var paramsList [][]interface{}
	var insertedRecords []map[string]interface{}

	for i := 0; i < dp.NumRecords; i++ {
		// Generate a record with NULL for circular foreign keys
		record, params := dp.generateRecordWithNullCircularFKs(table, columnNames, columnObjects, nonCircularFKs, circularFKs)
		
		if params != nil {
			paramsList = append(paramsList, params)
			insertedRecords = append(insertedRecords, record)
		}

		// Insert in batches of 100 records
		if len(paramsList) >= 100 || (i == dp.NumRecords-1 && len(paramsList) > 0) {
			_, err := dp.DB.ExecuteMany(insertSQL, paramsList)
			if err != nil {
				dp.Logger.Errorf("Error inserting data into table %s (first pass): %v", table, err)
				return false
			}

			// Store inserted data for reference
			dp.InsertedData[table] = append(dp.InsertedData[table], insertedRecords...)

			// Reset for next batch
			paramsList = nil
			insertedRecords = nil
		}
	}

	// Second pass: Update records with valid foreign keys
	dp.Logger.Infof("Second pass: Updating records with valid circular foreign keys")
	for _, fk := range circularFKs {
		// Skip if the referenced table has no data
		if len(dp.InsertedData[fk.ReferencedTable]) == 0 {
			dp.Logger.Warningf("Referenced table %s has no data, skipping update for %s.%s",
				fk.ReferencedTable, table, fk.Column)
			continue
		}

		// Get primary key column for this table
		var pkColumn string
		for _, col := range columns {
			if col.ColumnKey == "PRI" {
				pkColumn = col.Name
				break
			}
		}

		if pkColumn == "" {
			dp.Logger.Warningf("No primary key found for table %s, skipping update", table)
			continue
		}

		// Update each record with a random value from the referenced table
		for _, record := range dp.InsertedData[table] {
			// Get a random record from the referenced table
			referencedRecords := dp.InsertedData[fk.ReferencedTable]
			if len(referencedRecords) == 0 {
				continue
			}

			// Get the primary key value for this record
			pkValue := record[pkColumn]
			if pkValue == nil {
				continue
			}

			// Get a random referenced value
			referencedRecord := referencedRecords[time.Now().Nanosecond()%len(referencedRecords)]
			referencedValue := referencedRecord[fk.ReferencedColumn]
			if referencedValue == nil {
				continue
			}

			// Update the record
			updateSQL := fmt.Sprintf(
				"UPDATE %s SET %s = ? WHERE %s = ?",
				table,
				fk.Column,
				pkColumn,
			)

			_, err := dp.DB.ExecuteStatement(updateSQL, referencedValue, pkValue)
			if err != nil {
				dp.Logger.Errorf("Error updating circular foreign key %s.%s: %v", table, fk.Column, err)
				// Continue with other records
			}
		}
	}

	dp.Logger.Infof("Successfully populated circular dependency table %s with %d records", table, dp.NumRecords)
	return true
}

// generateRecord generates a single record for a table
func (dp *DatabasePopulator) generateRecord(
	table string,
	columnNames []string,
	columns []models.Column,
	foreignKeys []models.ForeignKey,
) (map[string]interface{}, []interface{}) {
	record := make(map[string]interface{})
	var params []interface{}

	// Create a map of foreign key columns for quick lookup
	fkMap := make(map[string]models.ForeignKey)
	for _, fk := range foreignKeys {
		fkMap[fk.Column] = fk
	}

	// Generate data for each column
	for i, columnName := range columnNames {
		column := columns[i]
		var value interface{}

		// Check if this is a foreign key
		if fk, isFk := fkMap[columnName]; isFk {
			// Get a random value from the referenced table
			value = dp.getRandomForeignKeyValue(fk)
			
			// If no value is available and the column is NOT NULL, this is a problem
			if value == nil && !column.IsNullable {
				dp.Logger.Errorf("No value available for NOT NULL foreign key %s.%s referencing %s.%s",
					table, columnName, fk.ReferencedTable, fk.ReferencedColumn)
				return nil, nil
			}
		} else {
			// Generate a value based on column type
			value = dp.DataGenerator.GenerateData(table, column)
		}

		record[columnName] = value
		params = append(params, value)
	}

	return record, params
}

// generateRecordWithNullCircularFKs generates a record with NULL values for circular foreign keys
func (dp *DatabasePopulator) generateRecordWithNullCircularFKs(
	table string,
	columnNames []string,
	columns []models.Column,
	nonCircularFKs []models.ForeignKey,
	circularFKs []models.ForeignKey,
) (map[string]interface{}, []interface{}) {
	record := make(map[string]interface{})
	var params []interface{}

	// Create maps for foreign key columns
	nonCircularFKMap := make(map[string]models.ForeignKey)
	for _, fk := range nonCircularFKs {
		nonCircularFKMap[fk.Column] = fk
	}

	circularFKMap := make(map[string]models.ForeignKey)
	for _, fk := range circularFKs {
		circularFKMap[fk.Column] = fk
	}

	// Generate data for each column
	for i, columnName := range columnNames {
		column := columns[i]
		var value interface{}

		// Check if this is a non-circular foreign key
		if fk, isFk := nonCircularFKMap[columnName]; isFk {
			// Get a random value from the referenced table
			value = dp.getRandomForeignKeyValue(fk)
			
			// If no value is available and the column is NOT NULL, this is a problem
			if value == nil && !column.IsNullable {
				dp.Logger.Errorf("No value available for NOT NULL foreign key %s.%s referencing %s.%s",
					table, columnName, fk.ReferencedTable, fk.ReferencedColumn)
				return nil, nil
			}
		} else if _, isCircularFK := circularFKMap[columnName]; isCircularFK {
			// Set circular foreign keys to NULL for now
			if !column.IsNullable {
				// If the column is NOT NULL, we need to handle it differently
				// For the first pass, we'll use a temporary value that will be updated later
				// This might violate constraints temporarily but will be fixed in the second pass
				value = dp.DataGenerator.GenerateData(table, column)
			} else {
				value = nil
			}
		} else {
			// Generate a value based on column type
			value = dp.DataGenerator.GenerateData(table, column)
		}

		record[columnName] = value
		params = append(params, value)
	}

	return record, params
}

// getRandomForeignKeyValue gets a random value from a referenced table
func (dp *DatabasePopulator) getRandomForeignKeyValue(fk models.ForeignKey) interface{} {
	// Check if we have inserted data for the referenced table
	referencedRecords, ok := dp.InsertedData[fk.ReferencedTable]
	if !ok || len(referencedRecords) == 0 {
		return nil
	}

	// Get a random record
	randomIndex := time.Now().Nanosecond() % len(referencedRecords)
	randomRecord := referencedRecords[randomIndex]

	// Return the referenced column value
	return randomRecord[fk.ReferencedColumn]
}

// calculateManyToManyRecords calculates how many records to insert for a many-to-many table
func (dp *DatabasePopulator) calculateManyToManyRecords(table string, foreignKeys []models.ForeignKey) int {
	// Get unique referenced tables
	referencedTables := make(map[string]bool)
	for _, fk := range foreignKeys {
		referencedTables[fk.ReferencedTable] = true
	}

	// Calculate based on the number of records in referenced tables
	var totalPossibleCombinations int = 1
	var availableReferencedTables int = 0

	for refTable := range referencedTables {
		refRecords, ok := dp.InsertedData[refTable]
		if ok && len(refRecords) > 0 {
			totalPossibleCombinations *= len(refRecords)
			availableReferencedTables++
		}
	}

	// If not all referenced tables have data, return 0
	if availableReferencedTables < len(referencedTables) {
		return 0
	}

	// Calculate a reasonable number of records
	// Use the smaller of: total possible combinations or 2*NumRecords
	if totalPossibleCombinations > 2*dp.NumRecords {
		return 2 * dp.NumRecords
	}
	return totalPossibleCombinations
}
