package generator

import (
	"encoding/json"
	"fmt"
	"math/rand"
	"regexp"
	"strings"
	"time"

	"github.com/jaswdr/faker"
	"github.com/sirupsen/logrus"
	"github.com/vitebski/mysql-dummy-populator/internal/analyzer"
	"github.com/vitebski/mysql-dummy-populator/pkg/models"
)

// DataGenerator generates fake data based on column types and constraints
type DataGenerator struct {
	Faker          faker.Faker
	SchemaAnalyzer *analyzer.SchemaAnalyzer
	CurrentRecord  map[string]interface{}
	Logger         *logrus.Logger
}

// NewDataGenerator creates a new data generator
func NewDataGenerator(schemaAnalyzer *analyzer.SchemaAnalyzer, logger *logrus.Logger) *DataGenerator {
	return &DataGenerator{
		Faker:          faker.New(),
		SchemaAnalyzer: schemaAnalyzer,
		CurrentRecord:  make(map[string]interface{}),
		Logger:         logger,
	}
}

// GenerateData generates data for a column based on its type and constraints
func (dg *DataGenerator) GenerateData(table string, column models.Column) interface{} {
	// Reset current record for each new record
	if len(dg.CurrentRecord) > 10 {
		dg.CurrentRecord = make(map[string]interface{})
	}

	// Check for special column names
	columnName := strings.ToLower(column.Name)
	dataType := strings.ToLower(column.DataType)

	// Handle special column names
	if strings.Contains(columnName, "email") {
		return dg.Faker.Internet().Email()
	} else if strings.Contains(columnName, "name") && !strings.Contains(columnName, "file") {
		if strings.Contains(columnName, "first") {
			return dg.Faker.Person().FirstName()
		} else if strings.Contains(columnName, "last") {
			return dg.Faker.Person().LastName()
		} else if strings.Contains(columnName, "full") {
			return dg.Faker.Person().Name()
		} else if strings.Contains(columnName, "user") {
			return dg.Faker.Internet().User()
		} else if strings.Contains(columnName, "company") || strings.Contains(columnName, "business") {
			return dg.Faker.Company().Name()
		} else {
			return dg.Faker.Person().Name()
		}
	} else if strings.Contains(columnName, "phone") {
		return dg.Faker.Phone().Number()
	} else if strings.Contains(columnName, "address") {
		return dg.Faker.Address().Address()
	} else if strings.Contains(columnName, "city") {
		return dg.Faker.Address().City()
	} else if strings.Contains(columnName, "state") {
		return dg.Faker.Address().State()
	} else if strings.Contains(columnName, "country") {
		return dg.Faker.Address().Country()
	} else if strings.Contains(columnName, "zip") || strings.Contains(columnName, "postal") {
		return dg.Faker.Address().PostCode()
	} else if strings.Contains(columnName, "lat") || strings.Contains(columnName, "latitude") {
		return dg.Faker.Address().Latitude()
	} else if strings.Contains(columnName, "lon") || strings.Contains(columnName, "longitude") {
		return dg.Faker.Address().Longitude()
	} else if strings.Contains(columnName, "description") || strings.Contains(columnName, "summary") {
		return dg.Faker.Lorem().Paragraph(3)
	} else if strings.Contains(columnName, "title") {
		return dg.Faker.Lorem().Sentence(4)
	} else if strings.Contains(columnName, "url") || strings.Contains(columnName, "website") {
		return dg.Faker.Internet().URL()
	} else if strings.Contains(columnName, "ip") {
		return dg.Faker.Internet().Ipv4()
	} else if strings.Contains(columnName, "password") {
		return dg.Faker.Internet().Password()
	} else if strings.Contains(columnName, "token") {
		return dg.Faker.RandomStringWithLength(32)
	} else if strings.Contains(columnName, "color") {
		return dg.Faker.Color().Hex()
	} else if strings.Contains(columnName, "filename") || strings.Contains(columnName, "file_name") {
		return dg.Faker.File().FilenameWithExtension()
	} else if strings.Contains(columnName, "mimetype") || strings.Contains(columnName, "mime_type") {
		return "application/" + dg.Faker.Lorem().Word()
	} else if strings.Contains(columnName, "uuid") {
		return dg.Faker.UUID().V4()
	} else if strings.Contains(columnName, "created_at") || strings.Contains(columnName, "updated_at") {
		return time.Now().Add(-time.Duration(rand.Intn(30)) * 24 * time.Hour)
	} else if strings.Contains(columnName, "deleted_at") {
		// 70% chance of being null for deleted_at
		if rand.Float32() < 0.7 {
			return nil
		}
		return time.Now().Add(-time.Duration(rand.Intn(10)) * 24 * time.Hour)
	}

	// Generate data based on data type
	switch dataType {
	case "varchar", "char", "text", "tinytext", "mediumtext", "longtext":
		return dg.generateString(column)
	case "int", "tinyint", "smallint", "mediumint", "bigint":
		return dg.generateInteger(column)
	case "float", "double", "decimal":
		return dg.generateFloat(column)
	case "date":
		return dg.generateDate()
	case "time":
		return dg.generateTime()
	case "datetime", "timestamp":
		return dg.generateDateTime()
	case "year":
		return dg.generateYear()
	case "enum":
		return dg.generateEnum(column)
	case "set":
		return dg.generateSet(column)
	case "bit":
		return dg.generateBit(column)
	case "binary", "varbinary":
		return dg.generateBinary(column)
	case "blob", "tinyblob", "mediumblob", "longblob":
		return dg.generateBlob(column)
	case "json":
		return dg.generateJSON(column)
	case "point", "linestring", "polygon", "geometry", "multipoint", "multilinestring", "multipolygon", "geometrycollection":
		return dg.generateSpatial(column)
	case "boolean", "bool":
		return rand.Intn(2) == 1
	default:
		dg.Logger.Warningf("No specific generator for type %s, using default string", dataType)
		return dg.Faker.Lorem().Word()
	}
}

// generateString generates a string value based on column constraints
func (dg *DataGenerator) generateString(column models.Column) string {
	var maxLength int64 = 255
	if column.CharMaxLength != nil {
		maxLength = *column.CharMaxLength
	} else {
		// Set reasonable defaults based on type
		switch strings.ToLower(column.DataType) {
		case "tinytext":
			maxLength = 255
		case "text":
			maxLength = 1000 // Don't generate full 65535 chars
		case "mediumtext":
			maxLength = 2000 // Don't generate full 16777215 chars
		case "longtext":
			maxLength = 3000 // Don't generate full 4294967295 chars
		}
	}

	// Limit max length to something reasonable
	if maxLength > 1000 {
		maxLength = 1000
	}

	// Generate a random length between 1 and maxLength
	length := rand.Int63n(maxLength) + 1
	if length > 100 {
		length = 100 // Keep it reasonable
	}

	// For very short fields, use more specific generators
	if length <= 5 {
		return dg.Faker.RandomStringWithLength(int(length))
	} else if length <= 10 {
		return dg.Faker.Lorem().Word()
	} else if length <= 50 {
		return dg.Faker.Lorem().Sentence(int(length / 10))
	} else {
		return dg.Faker.Lorem().Paragraph(int(length / 30))
	}
}

// generateInteger generates an integer value based on column constraints
func (dg *DataGenerator) generateInteger(column models.Column) interface{} {
	// Check for boolean tinyint
	if strings.ToLower(column.DataType) == "tinyint" && strings.Contains(strings.ToLower(column.ColumnType), "tinyint(1)") {
		return rand.Intn(2)
	}

	// Check for auto_increment
	if strings.Contains(strings.ToLower(column.Extra), "auto_increment") {
		return nil // Let MySQL handle auto_increment
	}

	// Generate based on type
	switch strings.ToLower(column.DataType) {
	case "tinyint":
		if strings.Contains(strings.ToLower(column.ColumnType), "unsigned") {
			return uint8(rand.Intn(256))
		}
		return int8(rand.Intn(256) - 128)
	case "smallint":
		if strings.Contains(strings.ToLower(column.ColumnType), "unsigned") {
			return uint16(rand.Intn(65536))
		}
		return int16(rand.Intn(65536) - 32768)
	case "mediumint":
		if strings.Contains(strings.ToLower(column.ColumnType), "unsigned") {
			return uint32(rand.Intn(16777216))
		}
		return int32(rand.Intn(16777216) - 8388608)
	case "int":
		if strings.Contains(strings.ToLower(column.ColumnType), "unsigned") {
			return uint32(rand.Uint32())
		}
		return int32(rand.Int31())
	case "bigint":
		if strings.Contains(strings.ToLower(column.ColumnType), "unsigned") {
			return uint64(rand.Uint64())
		}
		return int64(rand.Int63())
	default:
		return rand.Int31()
	}
}

// generateFloat generates a float value based on column constraints
func (dg *DataGenerator) generateFloat(column models.Column) interface{} {
	// Generate a random float
	value := rand.Float64() * 1000

	// Round based on scale if available
	if column.NumericScale != nil {
		scale := *column.NumericScale
		multiplier := 1.0
		for i := int64(0); i < scale; i++ {
			multiplier *= 10
		}
		value = float64(int64(value*multiplier)) / multiplier
	}

	return value
}

// generateDate generates a random date
func (dg *DataGenerator) generateDate() time.Time {
	// Generate a date within the last 5 years
	days := rand.Intn(365 * 5)
	return time.Now().AddDate(0, 0, -days)
}

// generateTime generates a random time
func (dg *DataGenerator) generateTime() string {
	hour := rand.Intn(24)
	minute := rand.Intn(60)
	second := rand.Intn(60)
	return fmt.Sprintf("%02d:%02d:%02d", hour, minute, second)
}

// generateDateTime generates a random datetime
func (dg *DataGenerator) generateDateTime() time.Time {
	// Generate a datetime within the last 5 years
	days := rand.Intn(365 * 5)
	hours := rand.Intn(24)
	minutes := rand.Intn(60)
	seconds := rand.Intn(60)

	return time.Now().
		AddDate(0, 0, -days).
		Add(-time.Duration(hours) * time.Hour).
		Add(-time.Duration(minutes) * time.Minute).
		Add(-time.Duration(seconds) * time.Second)
}

// generateYear generates a random year
func (dg *DataGenerator) generateYear() int {
	// Generate a year between 1970 and current year
	currentYear := time.Now().Year()
	return rand.Intn(currentYear-1970+1) + 1970
}

// generateEnum generates a random enum value
func (dg *DataGenerator) generateEnum(column models.Column) string {
	// Extract enum values from column type
	// Format is typically: "enum('value1','value2','value3')"
	enumRegex := regexp.MustCompile(`enum\((.+)\)`)
	matches := enumRegex.FindStringSubmatch(column.ColumnType)

	if len(matches) < 2 {
		return ""
	}

	// Split the values and remove quotes
	valuesStr := matches[1]
	valueRegex := regexp.MustCompile(`'([^']*)'`)
	valueMatches := valueRegex.FindAllStringSubmatch(valuesStr, -1)

	var values []string
	for _, match := range valueMatches {
		if len(match) >= 2 {
			values = append(values, match[1])
		}
	}

	if len(values) == 0 {
		return ""
	}

	// Return a random value
	return values[rand.Intn(len(values))]
}

// generateSet generates a random set value
func (dg *DataGenerator) generateSet(column models.Column) string {
	// Extract set values from column type
	// Format is typically: "set('value1','value2','value3')"
	setRegex := regexp.MustCompile(`set\((.+)\)`)
	matches := setRegex.FindStringSubmatch(column.ColumnType)

	if len(matches) < 2 {
		return ""
	}

	// Split the values and remove quotes
	valuesStr := matches[1]
	valueRegex := regexp.MustCompile(`'([^']*)'`)
	valueMatches := valueRegex.FindAllStringSubmatch(valuesStr, -1)

	var values []string
	for _, match := range valueMatches {
		if len(match) >= 2 {
			values = append(values, match[1])
		}
	}

	if len(values) == 0 {
		return ""
	}

	// Select a random number of values (1 to all)
	numValues := rand.Intn(len(values)) + 1
	selectedIndices := rand.Perm(len(values))[:numValues]

	var selectedValues []string
	for _, idx := range selectedIndices {
		selectedValues = append(selectedValues, values[idx])
	}

	return strings.Join(selectedValues, ",")
}

// generateBit generates a random bit value
func (dg *DataGenerator) generateBit(column models.Column) interface{} {
	// Extract the bit length from column type
	// Format is typically: "bit(n)"
	bitRegex := regexp.MustCompile(`bit\((\d+)\)`)
	matches := bitRegex.FindStringSubmatch(column.ColumnType)

	var length int = 1
	if len(matches) >= 2 {
		fmt.Sscanf(matches[1], "%d", &length)
	}

	// Generate a random bit value
	if length == 1 {
		return rand.Intn(2)
	}

	// For longer bit fields, return a byte array
	bytes := make([]byte, (length+7)/8)
	rand.Read(bytes)
	return bytes
}

// generateBinary generates random binary data
func (dg *DataGenerator) generateBinary(column models.Column) []byte {
	var length int64 = 10
	if column.CharMaxLength != nil {
		length = *column.CharMaxLength
	}

	// Limit to a reasonable size
	if length > 100 {
		length = 100
	}

	data := make([]byte, length)
	rand.Read(data)
	return data
}

// generateBlob generates random blob data
func (dg *DataGenerator) generateBlob(column models.Column) []byte {
	var length int

	// Set reasonable defaults based on type
	switch strings.ToLower(column.DataType) {
	case "tinyblob":
		length = 255
	case "blob":
		length = 500
	case "mediumblob":
		length = 1000
	case "longblob":
		length = 2000
	default:
		length = 500
	}

	data := make([]byte, length)
	rand.Read(data)
	return data
}

// generateJSON generates random JSON data
func (dg *DataGenerator) generateJSON(column models.Column) string {
	columnName := strings.ToLower(column.Name)

	var data interface{}

	if strings.Contains(columnName, "address") {
		// Generate address JSON
		data = map[string]interface{}{
			"street":  dg.Faker.Address().StreetAddress(),
			"city":    dg.Faker.Address().City(),
			"state":   dg.Faker.Address().State(),
			"zipCode": dg.Faker.Address().PostCode(),
			"country": dg.Faker.Address().Country(),
		}
	} else if strings.Contains(columnName, "person") || strings.Contains(columnName, "user") {
		// Generate person JSON
		data = map[string]interface{}{
			"firstName": dg.Faker.Person().FirstName(),
			"lastName":  dg.Faker.Person().LastName(),
			"email":     dg.Faker.Internet().Email(),
			"phone":     dg.Faker.Phone().Number(),
		}
	} else if strings.Contains(columnName, "product") {
		// Generate product JSON
		data = map[string]interface{}{
			"name":        dg.Faker.Lorem().Word(),
			"price":       fmt.Sprintf("%.2f", rand.Float64()*1000),
			"description": dg.Faker.Lorem().Sentence(10),
			"category":    dg.Faker.Lorem().Word(),
		}
	} else if strings.Contains(columnName, "meta") || strings.Contains(columnName, "attributes") {
		// Generate metadata JSON
		data = map[string]interface{}{
			"created":  dg.Faker.Time().ISO8601(time.Now().AddDate(0, 0, -rand.Intn(365))),
			"modified": dg.Faker.Time().ISO8601(time.Now().AddDate(0, 0, -rand.Intn(30))),
			"author":   dg.Faker.Person().Name(),
			"version":  fmt.Sprintf("%d.%d.%d", rand.Intn(10), rand.Intn(10), rand.Intn(10)),
		}
	} else if strings.Contains(columnName, "dimension") {
		// Generate dimensions JSON
		data = map[string]interface{}{
			"width":  rand.Float64() * 100,
			"height": rand.Float64() * 100,
			"depth":  rand.Float64() * 50,
			"weight": rand.Float64() * 20,
			"unit":   "cm",
		}
	} else if strings.Contains(columnName, "tags") {
		// Generate tags as JSON array
		categories := []string{"electronics", "clothing", "home", "books", "sports"}
		features := []string{"new", "sale", "popular", "trending", "limited"}

		var tags []string
		for i := 0; i < rand.Intn(3)+1; i++ {
			tags = append(tags, categories[rand.Intn(len(categories))])
		}
		for i := 0; i < rand.Intn(2)+1; i++ {
			tags = append(tags, features[rand.Intn(len(features))])
		}

		data = tags
	} else if strings.Contains(columnName, "options") {
		// Generate selected product options
		data = map[string]interface{}{
			"color": []string{"black", "white", "red", "blue", "green"}[rand.Intn(5)],
			"size":  []string{"S", "M", "L", "XL"}[rand.Intn(4)],
		}
	} else {
		// Generate generic JSON
		data = map[string]interface{}{
			"id":      rand.Intn(1000),
			"name":    dg.Faker.Lorem().Word(),
			"value":   dg.Faker.Lorem().Sentence(5),
			"enabled": rand.Intn(2) == 1,
		}
	}

	jsonBytes, err := json.Marshal(data)
	if err != nil {
		dg.Logger.Errorf("Error generating JSON: %v", err)
		return "{}"
	}

	return string(jsonBytes)
}

// generateSpatial generates random spatial data
func (dg *DataGenerator) generateSpatial(column models.Column) string {
	dataType := strings.ToLower(column.DataType)

	switch dataType {
	case "point":
		// Generate a random point
		lat := rand.Float64()*180 - 90
		lng := rand.Float64()*360 - 180
		return fmt.Sprintf("POINT(%f %f)", lng, lat)
	case "linestring":
		// Generate a random linestring with 2-5 points
		numPoints := rand.Intn(4) + 2
		var points []string
		for i := 0; i < numPoints; i++ {
			lat := rand.Float64()*180 - 90
			lng := rand.Float64()*360 - 180
			points = append(points, fmt.Sprintf("%f %f", lng, lat))
		}
		return fmt.Sprintf("LINESTRING(%s)", strings.Join(points, ", "))
	case "polygon":
		// Generate a simple polygon (rectangle)
		lat1 := rand.Float64()*80 - 40
		lng1 := rand.Float64()*80 - 40
		lat2 := lat1 + rand.Float64()*10
		lng2 := lng1 + rand.Float64()*10

		return fmt.Sprintf("POLYGON((%f %f, %f %f, %f %f, %f %f, %f %f))",
			lng1, lat1, lng2, lat1, lng2, lat2, lng1, lat2, lng1, lat1)
	default:
		// For other spatial types, return a simple point
		lat := rand.Float64()*180 - 90
		lng := rand.Float64()*360 - 180
		return fmt.Sprintf("POINT(%f %f)", lng, lat)
	}
}
