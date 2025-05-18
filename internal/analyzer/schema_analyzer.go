package analyzer

import (
	"fmt"
	"sort"
	"strconv"

	"github.com/sirupsen/logrus"
	"github.com/yourbasic/graph"
	"github.com/vitebski/mysql-dummy-populator/internal/connector"
	"github.com/vitebski/mysql-dummy-populator/pkg/models"
)

// SchemaAnalyzer analyzes database schema, detects dependencies, and sorts tables for population
type SchemaAnalyzer struct {
	DB                     *connector.DatabaseConnector
	Tables                 []string
	Views                  []string
	ForeignKeys            map[string][]models.ForeignKey
	ManyToManyTables       map[string]bool
	TableColumns           map[string][]models.Column
	DependencyGraph        *graph.Mutable
	TableIndexMap          map[string]int
	IndexTableMap          map[int]string
	DirectCircularDeps     [][]string
	Logger                 *logrus.Logger
	CheckConstraints       map[string]map[string]string
}

// NewSchemaAnalyzer creates a new schema analyzer
func NewSchemaAnalyzer(db *connector.DatabaseConnector, logger *logrus.Logger) *SchemaAnalyzer {
	return &SchemaAnalyzer{
		DB:               db,
		ForeignKeys:      make(map[string][]models.ForeignKey),
		ManyToManyTables: make(map[string]bool),
		TableColumns:     make(map[string][]models.Column),
		TableIndexMap:    make(map[string]int),
		IndexTableMap:    make(map[int]string),
		Logger:           logger,
		CheckConstraints: make(map[string]map[string]string),
	}
}

// AnalyzeSchema analyzes the database schema
func (sa *SchemaAnalyzer) AnalyzeSchema() error {
	// Get all tables
	tablesQuery := `
		SELECT table_name
		FROM information_schema.tables
		WHERE table_schema = ?
		AND table_type = 'BASE TABLE'
		ORDER BY table_name
	`
	tablesResult, err := sa.DB.ExecuteQuery(tablesQuery, sa.DB.Database)
	if err != nil {
		sa.Logger.Errorf("Error getting tables: %v", err)
		return err
	}

	for _, row := range tablesResult {
		sa.Tables = append(sa.Tables, row["table_name"].(string))
	}

	// Get all views
	viewsQuery := `
		SELECT table_name
		FROM information_schema.tables
		WHERE table_schema = ?
		AND table_type = 'VIEW'
		ORDER BY table_name
	`
	viewsResult, err := sa.DB.ExecuteQuery(viewsQuery, sa.DB.Database)
	if err != nil {
		sa.Logger.Errorf("Error getting views: %v", err)
		return err
	}

	for _, row := range viewsResult {
		sa.Views = append(sa.Views, row["table_name"].(string))
	}

	// Get all columns for each table
	for _, table := range sa.Tables {
		columnsQuery := `
			SELECT
				column_name,
				data_type,
				column_type,
				character_maximum_length,
				numeric_precision,
				numeric_scale,
				is_nullable,
				column_key,
				extra,
				column_comment
			FROM information_schema.columns
			WHERE table_schema = ?
			AND table_name = ?
			ORDER BY ordinal_position
		`
		columnsResult, err := sa.DB.ExecuteQuery(columnsQuery, sa.DB.Database, table)
		if err != nil {
			sa.Logger.Warningf("Failed to retrieve columns for table %s: %v", table, err)
			continue
		}

		var columns []models.Column
		for _, row := range columnsResult {
			var charMaxLength, numericPrecision, numericScale *int64

			if row["character_maximum_length"] != nil {
				val, _ := strconv.ParseInt(fmt.Sprintf("%v", row["character_maximum_length"]), 10, 64)
				charMaxLength = &val
			}

			if row["numeric_precision"] != nil {
				val, _ := strconv.ParseInt(fmt.Sprintf("%v", row["numeric_precision"]), 10, 64)
				numericPrecision = &val
			}

			if row["numeric_scale"] != nil {
				val, _ := strconv.ParseInt(fmt.Sprintf("%v", row["numeric_scale"]), 10, 64)
				numericScale = &val
			}

			column := models.Column{
				Name:              row["column_name"].(string),
				DataType:          row["data_type"].(string),
				ColumnType:        row["column_type"].(string),
				CharMaxLength:     charMaxLength,
				NumericPrecision:  numericPrecision,
				NumericScale:      numericScale,
				IsNullable:        row["is_nullable"].(string) == "YES",
				ColumnKey:         row["column_key"].(string),
				Extra:             row["extra"].(string),
				ColumnComment:     row["column_comment"].(string),
			}

			columns = append(columns, column)
		}

		sa.TableColumns[table] = columns
	}

	// Get all foreign keys
	fkQuery := `
		SELECT
			table_name,
			column_name,
			referenced_table_name,
			referenced_column_name,
			constraint_name
		FROM information_schema.key_column_usage
		WHERE table_schema = ?
		AND referenced_table_name IS NOT NULL
		ORDER BY table_name, column_name
	`
	fkResult, err := sa.DB.ExecuteQuery(fkQuery, sa.DB.Database)
	if err != nil {
		sa.Logger.Errorf("Error getting foreign keys: %v", err)
		return err
	}

	// Create a map of table indices for the dependency graph
	for i, table := range sa.Tables {
		sa.TableIndexMap[table] = i
		sa.IndexTableMap[i] = table
	}

	// Initialize the dependency graph
	sa.DependencyGraph = graph.New(len(sa.Tables))

	// Process foreign keys
	for _, row := range fkResult {
		tableName := row["table_name"].(string)
		columnName := row["column_name"].(string)
		referencedTable := row["referenced_table_name"].(string)
		referencedColumn := row["referenced_column_name"].(string)
		constraintName := row["constraint_name"].(string)

		// Find if the column is nullable
		isNullable := false
		for _, col := range sa.TableColumns[tableName] {
			if col.Name == columnName {
				isNullable = col.IsNullable
				break
			}
		}

		// Create foreign key object
		fk := models.ForeignKey{
			Table:            tableName,
			Column:           columnName,
			ReferencedTable:  referencedTable,
			ReferencedColumn: referencedColumn,
			IsNullable:       isNullable,
			ConstraintName:   constraintName,
		}

		// Add to foreign keys map
		sa.ForeignKeys[tableName] = append(sa.ForeignKeys[tableName], fk)

		// Add edge to dependency graph
		// Use weight=1 for mandatory (NOT NULL) foreign keys
		// Use weight=2 for optional (nullable) foreign keys
		weight := int64(2)
		if !isNullable {
			weight = int64(1)
		}

		// Add edge if both tables exist in our table list
		if srcIdx, ok := sa.TableIndexMap[tableName]; ok {
			if destIdx, ok := sa.TableIndexMap[referencedTable]; ok {
				sa.DependencyGraph.AddCost(srcIdx, destIdx, weight)
			}
		}
	}

	// Detect many-to-many relationship tables
	sa.detectManyToManyTables()

	// Extract and analyze check constraints
	sa.extractCheckConstraints()

	return nil
}

// detectManyToManyTables detects tables that represent many-to-many relationships
func (sa *SchemaAnalyzer) detectManyToManyTables() {
	for _, table := range sa.Tables {
		// Skip tables without foreign keys
		fks, hasFKs := sa.ForeignKeys[table]
		if !hasFKs {
			continue
		}

		// Get all columns for this table
		columns := sa.TableColumns[table]
		if len(columns) == 0 {
			continue
		}

		// Count primary key columns
		pkColumns := 0
		for _, col := range columns {
			if col.ColumnKey == "PRI" {
				pkColumns++
			}
		}

		// Check if this might be a many-to-many table:
		// 1. Has at least 2 foreign keys
		// 2. Number of foreign keys is close to total columns
		// 3. Number of foreign keys is close to number of primary key columns
		if len(fks) >= 2 && float64(len(fks))/float64(len(columns)) >= 0.5 && pkColumns >= len(fks)-1 {
			// Check if it references at least 2 different tables
			referencedTables := make(map[string]bool)
			for _, fk := range fks {
				referencedTables[fk.ReferencedTable] = true
			}

			if len(referencedTables) >= 2 {
				sa.ManyToManyTables[table] = true
			}
		}
	}
}

// extractCheckConstraints extracts check constraints from the database
func (sa *SchemaAnalyzer) extractCheckConstraints() {
	// This query works for MySQL 8.0+
	checkQuery := `
		SELECT
			t.table_name,
			c.constraint_name,
			c.check_clause
		FROM information_schema.check_constraints c
		JOIN information_schema.table_constraints t
		ON c.constraint_schema = t.constraint_schema
		AND c.constraint_name = t.constraint_name
		WHERE c.constraint_schema = ?
	`

	checkResult, err := sa.DB.ExecuteQuery(checkQuery, sa.DB.Database)
	if err != nil {
		sa.Logger.Warningf("Error getting check constraints (this is expected for MySQL < 8.0): %v", err)
		return
	}

	for _, row := range checkResult {
		tableName := row["table_name"].(string)
		constraintName := row["constraint_name"].(string)
		checkClause := row["check_clause"].(string)

		if _, exists := sa.CheckConstraints[tableName]; !exists {
			sa.CheckConstraints[tableName] = make(map[string]string)
		}

		sa.CheckConstraints[tableName][constraintName] = checkClause
	}
}

// GetCircularTables returns tables involved in circular dependencies
func (sa *SchemaAnalyzer) GetCircularTables() map[string]bool {
	circularTables := make(map[string]bool)

	// Find strongly connected components (cycles) in the graph
	for i := 0; i < len(sa.Tables); i++ {
		for j := 0; j < len(sa.Tables); j++ {
			if i == j {
				continue
			}

			// Check if there's a path from i to j and from j to i
			if sa.DependencyGraph.Cost(i, j) < int64(1000000) && sa.DependencyGraph.Cost(j, i) < int64(1000000) {
				circularTables[sa.IndexTableMap[i]] = true
				circularTables[sa.IndexTableMap[j]] = true

				// Record direct circular dependency
				sa.DirectCircularDeps = append(sa.DirectCircularDeps, []string{
					sa.IndexTableMap[i], sa.IndexTableMap[j],
				})
			}
		}
	}

	return circularTables
}

// GetTableInsertionOrder determines the order in which tables should be populated
func (sa *SchemaAnalyzer) GetTableInsertionOrder() ([]string, map[string]bool) {
	// First, analyze circular dependencies
	circularTables := sa.GetCircularTables()

	// Create a list of tables without circular dependencies
	var nonCircularTables []string
	for _, table := range sa.Tables {
		if !circularTables[table] {
			nonCircularTables = append(nonCircularTables, table)
		}
	}

	// Sort non-circular tables based on dependencies
	var orderedTables []string

	// First, add tables without foreign keys
	for _, table := range nonCircularTables {
		if _, hasFKs := sa.ForeignKeys[table]; !hasFKs {
			orderedTables = append(orderedTables, table)
		}
	}

	// Then, add tables with foreign keys in dependency order
	var dependentTables []string
	for _, table := range nonCircularTables {
		if _, hasFKs := sa.ForeignKeys[table]; hasFKs {
			dependentTables = append(dependentTables, table)
		}
	}

	// Sort dependent tables based on their dependencies
	// This is a simplified topological sort
	for len(dependentTables) > 0 {
		// Find a table whose dependencies are all in orderedTables
		found := false
		for i, table := range dependentTables {
			allDepsResolved := true
			for _, fk := range sa.ForeignKeys[table] {
				// Skip self-references
				if fk.ReferencedTable == table {
					continue
				}

				// Check if the referenced table is already in orderedTables
				isResolved := false
				for _, orderedTable := range orderedTables {
					if fk.ReferencedTable == orderedTable {
						isResolved = true
						break
					}
				}

				if !isResolved {
					allDepsResolved = false
					break
				}
			}

			if allDepsResolved {
				orderedTables = append(orderedTables, table)
				dependentTables = append(dependentTables[:i], dependentTables[i+1:]...)
				found = true
				break
			}
		}

		// If no table was found, there might be a circular dependency
		// In this case, just add the remaining tables in any order
		if !found {
			orderedTables = append(orderedTables, dependentTables...)
			break
		}
	}

	// Finally, add tables with circular dependencies
	var circularTablesList []string
	for table := range circularTables {
		circularTablesList = append(circularTablesList, table)
	}

	// Sort circular tables by name for consistency
	sort.Strings(circularTablesList)
	orderedTables = append(orderedTables, circularTablesList...)

	// Move many-to-many tables to the end
	var finalOrderedTables []string
	var manyToManyTablesList []string

	for _, table := range orderedTables {
		if sa.ManyToManyTables[table] {
			manyToManyTablesList = append(manyToManyTablesList, table)
		} else {
			finalOrderedTables = append(finalOrderedTables, table)
		}
	}

	// Add many-to-many tables at the end
	finalOrderedTables = append(finalOrderedTables, manyToManyTablesList...)

	return finalOrderedTables, circularTables
}
