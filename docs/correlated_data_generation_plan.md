# Correlated Data Generation Feature Plan

## 1. Problem

Current data generation methods in the MySQL Dummy Data Populator primarily focus on generating data for individual columns based on their data types and constraints. While this ensures individual column validity, it does not account for the relationships and dependencies that often exist *between* columns within a table or across related tables. This can lead to the generation of dummy data that is logically inconsistent or unrealistic when viewed in context, reducing the effectiveness of the generated data for testing and development purposes. For example, generating a city and a corresponding postal code that do not match, or generating an order date that precedes the customer's join date.

## 2. Goal

The goal is to enhance the data generation process to produce dummy data where values in correlated columns are logically consistent and reflect plausible real-world relationships. This will improve the realism and utility of the generated data for database testing, application development, and demonstrations.

## 3. Design Approach

The design approach involves identifying and modeling correlations between columns and leveraging this information during the data generation process. This will be achieved through a combination of explicit user definition, potential inferred detection, the use of lookup tables, and conditional data generation logic.

### 3.1. Explicit Correlation Definition

This approach allows users to explicitly define correlations between columns, providing the highest level of control and accuracy.

*   **Mechanism:** Users can define correlations using:
    *   **Configuration File:** A dedicated section in a configuration file (e.g., YAML or JSON) where users specify correlated column groups and the type of correlation (e.g., `city`, `state`, `zip_code` are correlated via a lookup, `start_date` and `end_date` have a `start < end` dependency).
    *   **Schema Comments:** Extending the current schema comment parsing to include a defined syntax for specifying correlations directly in the database schema definition. This keeps correlation information tightly coupled with the relevant columns.
*   **SchemaAnalyzer Role:** The `SchemaAnalyzer` will be updated to parse and store these explicit correlation definitions. This information will then be accessible during the data generation phase.
*   **Benefits:** Provides precise control over correlated data generation, enabling users to model complex and domain-specific relationships accurately.

### 3.2. Inferred Correlation Detection (Optional/Future)

While less precise than explicit definition, the tool could attempt to infer potential correlations based on schema patterns.

*   **Mechanism:** The `SchemaAnalyzer` could employ heuristics such as:
    *   Analyzing column names for common patterns (e.g., columns named `*_city`, `*_state`, `*_zip`).
    *   Examining columns frequently involved in `JOIN` conditions in views or stored procedures (if accessible).
    *   Considering combinations of data types and naming conventions.
*   **Process:** Inferred correlations would be identified during schema analysis and potentially presented to the user as suggestions for explicit definition or confirmation.
*   **Benefits:** Can help users identify potential correlations they might not have considered and reduces the initial manual effort for simple, common correlations.

### 3.3. Lookup Tables and Data Dependencies

For correlations based on predefined sets of related values, the tool will utilize lookup tables.

*   **Mechanism:**
    *   **Internal Lookup Tables:** The tool can include built-in lookup tables for common correlated data sets (e.g., US cities, states, and zip codes; country codes and country names).
    *   **User-Provided Lookup Tables:** Allow users to provide custom lookup tables (e.g., CSV files) for domain-specific correlated data (e.g., product categories and subcategories, company names and industry types).
*   **Data Generation Process:** When generating data for a set of correlated columns defined to use a lookup, the `DataGenerator` will randomly select a valid row from the relevant lookup table and use those values for the corresponding columns in the generated record.
*   **Benefits:** Ensures that generated data combinations are always valid and realistic according to a defined set of possibilities.

### 3.4. Conditional Data Generation Logic

This involves adjusting the data generation for a column based on the value already generated for a correlated column within the same row or a related row.

*   **Mechanism:** The `DataGenerator`'s internal logic will be extended to handle dependencies between column generations.
    *   **Value Filtering/Constraining:** If column B is correlated with column A, after generating a value for A, the possible values or ranges for B are filtered or constrained based on A's value (e.g., if `state` is 'California', `city` must be a city in California).
    *   **Dependent Generators:** Specific data generators can be triggered or modified based on the value of a correlated column.
*   **Process:** The order of generation for correlated columns within a row might be important. The tool would determine a suitable order based on the defined dependencies.
*   **Benefits:** Allows for dynamic generation of correlated data where the relationship is based on rules or ranges rather than just fixed lookup values.

## 4. Implementation Considerations

*   **Data Structures for Correlations:** Designing efficient data structures to store and access correlation information (explicit and potentially inferred) is crucial.
*   **Integration with Existing Data Generation:** Modifying the `DataGenerator` to handle correlated groups of columns, potentially overriding or influencing existing single-column generation logic.
*   **Handling Complex and Circular Correlations:** Designing for scenarios involving multiple levels of correlation or correlations that form cycles will require careful planning and potentially multi-pass generation for correlated groups.
*   **Performance:** Ensuring that the overhead of correlation processing does not significantly impact the data generation speed, especially for large numbers of records.
*   **User Feedback and Validation:** Providing clear feedback to the user on identified or defined correlations and validating the correctness of user-provided definitions (e.g., ensuring lookup tables match column types).
*   **Error Handling:** Gracefully handling cases where correlations cannot be satisfied (e.g., no matching entries in a lookup table for a generated value).

## 5. Benefits for Users

Implementing correlated data generation will provide significant benefits:

*   **Increased Data Realism:** The generated dummy data will more closely resemble real-world data, including valid relationships between fields.
*   **More Effective Testing:** Tests using this data will be more representative of production scenarios, leading to better bug detection and confidence in application behavior.
*   **Reduced Manual Data Cleanup:** Users will spend less time manually correcting or validating the generated data to ensure consistency.
*   **Improved Database Demonstrations:** Populated databases will look more authentic and professional for demos and presentations.
*   **Support for Complex Schema Testing:** The tool will be better equipped to populate databases with complex interdependent data, which is challenging with uncorrelated data generation.
*   **Enhanced Customization:** Users gain powerful capabilities to tailor the data generation process to their specific database schema and testing needs.