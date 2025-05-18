package analyzer

import (
	"testing"

	"github.com/sirupsen/logrus"
	"github.com/vitebski/mysql-dummy-populator/internal/connector"
	"github.com/vitebski/mysql-dummy-populator/pkg/models"
	"github.com/yourbasic/graph"
)

// MockDatabaseConnector is a mock implementation of the DatabaseConnector
type MockDatabaseConnector struct {
	*connector.DatabaseConnector
	ExecuteQueryFunc func(query string, params ...interface{}) ([]map[string]interface{}, error)
}

func (m *MockDatabaseConnector) ExecuteQuery(query string, params ...interface{}) ([]map[string]interface{}, error) {
	return m.ExecuteQueryFunc(query, params...)
}

func TestNewSchemaAnalyzer(t *testing.T) {
	// Create a logger
	logger := logrus.New()
	logger.SetLevel(logrus.FatalLevel) // Suppress log output during tests

	// Create a mock database connector
	db := &connector.DatabaseConnector{
		Host:     "localhost",
		User:     "user",
		Password: "password",
		Database: "database",
		Port:     "3306",
		Logger:   logger,
	}

	// Create a new schema analyzer
	analyzer := NewSchemaAnalyzer(db, logger)

	// Check that the analyzer was created correctly
	if analyzer == nil {
		t.Error("Expected analyzer to be created, got nil")
	}
	if analyzer.DB != db {
		t.Error("Expected analyzer.DB to be the mock connector")
	}
	if analyzer.Logger != logger {
		t.Error("Expected analyzer.Logger to be the test logger")
	}
	if analyzer.ForeignKeys == nil {
		t.Error("Expected analyzer.ForeignKeys to be initialized")
	}
	if analyzer.ManyToManyTables == nil {
		t.Error("Expected analyzer.ManyToManyTables to be initialized")
	}
	if analyzer.TableColumns == nil {
		t.Error("Expected analyzer.TableColumns to be initialized")
	}
	if analyzer.TableIndexMap == nil {
		t.Error("Expected analyzer.TableIndexMap to be initialized")
	}
	if analyzer.IndexTableMap == nil {
		t.Error("Expected analyzer.IndexTableMap to be initialized")
	}
	if analyzer.CheckConstraints == nil {
		t.Error("Expected analyzer.CheckConstraints to be initialized")
	}
}

func TestDetectManyToManyTables(t *testing.T) {
	// Create a logger
	logger := logrus.New()
	logger.SetLevel(logrus.FatalLevel) // Suppress log output during tests

	// Create a mock database connector
	db := &connector.DatabaseConnector{
		Host:     "localhost",
		User:     "user",
		Password: "password",
		Database: "database",
		Port:     "3306",
		Logger:   logger,
	}

	// Create a new schema analyzer
	analyzer := NewSchemaAnalyzer(db, logger)

	// Set up test data
	analyzer.Tables = []string{"users", "posts", "user_posts"}

	// Set up foreign keys
	analyzer.ForeignKeys = map[string][]models.ForeignKey{
		"user_posts": {
			{
				Table:            "user_posts",
				Column:           "user_id",
				ReferencedTable:  "users",
				ReferencedColumn: "id",
				IsNullable:       false,
			},
			{
				Table:            "user_posts",
				Column:           "post_id",
				ReferencedTable:  "posts",
				ReferencedColumn: "id",
				IsNullable:       false,
			},
		},
	}

	// Set up table columns
	analyzer.TableColumns = map[string][]models.Column{
		"user_posts": {
			{
				Name:      "id",
				DataType:  "int",
				ColumnKey: "PRI",
			},
			{
				Name:      "user_id",
				DataType:  "int",
				ColumnKey: "MUL",
			},
			{
				Name:      "post_id",
				DataType:  "int",
				ColumnKey: "MUL",
			},
		},
	}

	// Call the method being tested
	analyzer.detectManyToManyTables()

	// Check the result
	if !analyzer.ManyToManyTables["user_posts"] {
		t.Error("Expected user_posts to be detected as a many-to-many table")
	}
}

func TestGetCircularTables(t *testing.T) {
	// Create a logger
	logger := logrus.New()
	logger.SetLevel(logrus.FatalLevel) // Suppress log output during tests

	// Create a mock database connector
	db := &connector.DatabaseConnector{
		Host:     "localhost",
		User:     "user",
		Password: "password",
		Database: "database",
		Port:     "3306",
		Logger:   logger,
	}

	// Create a new schema analyzer
	analyzer := NewSchemaAnalyzer(db, logger)

	// Set up test data
	analyzer.Tables = []string{"employees", "departments"}
	analyzer.TableIndexMap = map[string]int{
		"employees":   0,
		"departments": 1,
	}
	analyzer.IndexTableMap = map[int]string{
		0: "employees",
		1: "departments",
	}

	// Create a dependency graph with a circular dependency
	analyzer.DependencyGraph = graph.New(2)
	analyzer.DependencyGraph.AddCost(0, 1, 1)
	analyzer.DependencyGraph.AddCost(1, 0, 1)

	// Call the method being tested
	circularTables := analyzer.GetCircularTables()

	// Check the result
	if !circularTables["employees"] {
		t.Error("Expected employees to be detected as a circular table")
	}
	if !circularTables["departments"] {
		t.Error("Expected departments to be detected as a circular table")
	}
}

func TestGetTableInsertionOrder(t *testing.T) {
	// Create a logger
	logger := logrus.New()
	logger.SetLevel(logrus.FatalLevel) // Suppress log output during tests

	// Create a mock database connector
	db := &connector.DatabaseConnector{
		Host:     "localhost",
		User:     "user",
		Password: "password",
		Database: "database",
		Port:     "3306",
		Logger:   logger,
	}

	// Create a new schema analyzer
	analyzer := NewSchemaAnalyzer(db, logger)

	// Set up test data
	analyzer.Tables = []string{"users", "posts", "comments", "user_posts"}

	// Set up table index map
	analyzer.TableIndexMap = map[string]int{
		"users":      0,
		"posts":      1,
		"comments":   2,
		"user_posts": 3,
	}

	// Set up index table map
	analyzer.IndexTableMap = map[int]string{
		0: "users",
		1: "posts",
		2: "comments",
		3: "user_posts",
	}

	// Create a dependency graph
	analyzer.DependencyGraph = graph.New(4)
	// posts depends on users
	analyzer.DependencyGraph.AddCost(1, 0, 1)
	// comments depends on posts
	analyzer.DependencyGraph.AddCost(2, 1, 1)
	// user_posts depends on users and posts
	analyzer.DependencyGraph.AddCost(3, 0, 1)
	analyzer.DependencyGraph.AddCost(3, 1, 1)

	// Set up foreign keys
	analyzer.ForeignKeys = map[string][]models.ForeignKey{
		"posts": {
			{
				Table:            "posts",
				Column:           "user_id",
				ReferencedTable:  "users",
				ReferencedColumn: "id",
				IsNullable:       false,
			},
		},
		"comments": {
			{
				Table:            "comments",
				Column:           "post_id",
				ReferencedTable:  "posts",
				ReferencedColumn: "id",
				IsNullable:       false,
			},
		},
		"user_posts": {
			{
				Table:            "user_posts",
				Column:           "user_id",
				ReferencedTable:  "users",
				ReferencedColumn: "id",
				IsNullable:       false,
			},
			{
				Table:            "user_posts",
				Column:           "post_id",
				ReferencedTable:  "posts",
				ReferencedColumn: "id",
				IsNullable:       false,
			},
		},
	}

	// Set up many-to-many tables
	analyzer.ManyToManyTables = map[string]bool{
		"user_posts": true,
	}

	// Call the method being tested
	orderedTables, circularTables := analyzer.GetTableInsertionOrder()

	// Check the result
	if len(orderedTables) != 4 {
		t.Errorf("Expected 4 tables in the ordered list, got %d", len(orderedTables))
	}

	// Check that users comes before posts
	usersIndex := -1
	postsIndex := -1
	for i, table := range orderedTables {
		if table == "users" {
			usersIndex = i
		} else if table == "posts" {
			postsIndex = i
		}
	}
	if usersIndex == -1 {
		t.Error("Expected users to be in the ordered list")
	}
	if postsIndex == -1 {
		t.Error("Expected posts to be in the ordered list")
	}
	if usersIndex > postsIndex {
		t.Error("Expected users to come before posts in the ordered list")
	}

	// Check that posts comes before comments
	commentsIndex := -1
	for i, table := range orderedTables {
		if table == "comments" {
			commentsIndex = i
		}
	}
	if commentsIndex == -1 {
		t.Error("Expected comments to be in the ordered list")
	}
	if postsIndex > commentsIndex {
		t.Error("Expected posts to come before comments in the ordered list")
	}

	// Check that user_posts comes last (as it's a many-to-many table)
	userPostsIndex := -1
	for i, table := range orderedTables {
		if table == "user_posts" {
			userPostsIndex = i
		}
	}
	if userPostsIndex == -1 {
		t.Error("Expected user_posts to be in the ordered list")
	}
	if userPostsIndex != len(orderedTables)-1 {
		t.Error("Expected user_posts to be the last table in the ordered list")
	}

	// Check that there are no circular tables
	if len(circularTables) != 0 {
		t.Errorf("Expected 0 circular tables, got %d", len(circularTables))
	}
}
