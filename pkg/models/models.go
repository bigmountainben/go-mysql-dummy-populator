package models

// Column represents a database column with its properties
type Column struct {
	Name               string
	DataType           string
	ColumnType         string
	CharMaxLength      *int64
	NumericPrecision   *int64
	NumericScale       *int64
	IsNullable         bool
	ColumnKey          string
	Extra              string
	ColumnComment      string
}

// ForeignKey represents a foreign key relationship
type ForeignKey struct {
	Table             string
	Column            string
	ReferencedTable   string
	ReferencedColumn  string
	IsNullable        bool
	ConstraintName    string
}

// TableCategory represents the category of a table
type TableCategory int

const (
	Standalone TableCategory = iota
	Dependent
	ManyToMany
	Circular
)

// TableInfo represents information about a table
type TableInfo struct {
	Name     string
	Category TableCategory
	Columns  []Column
}

// SchemaInfo represents the analyzed database schema
type SchemaInfo struct {
	Tables            []string
	Views             []string
	ForeignKeys       map[string][]ForeignKey
	ManyToManyTables  map[string]bool
	CircularTables    map[string]bool
	TableColumns      map[string][]Column
	OrderedTables     []string
}

// PopulationResult represents the result of the population process
type PopulationResult struct {
	SuccessfulTables []string
	FailedTables     []string
	TotalRecords     int
}

// VerificationResult represents the result of the verification process
type VerificationResult struct {
	Success                 bool
	EmptyTables             []string
	PartiallyPopulatedTables map[string]int
}
