-- JSON schema for testing the MySQL Database Populator
-- This schema focuses on JSON data types and operations:
-- - JSON columns
-- - JSON path expressions
-- - Generated columns from JSON

-- Drop tables if they exist
DROP TABLE IF EXISTS product_reviews;
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS customers;

-- Create customers table with JSON for preferences and metadata
CREATE TABLE customers (
    customer_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    phone VARCHAR(20),
    address JSON NOT NULL COMMENT 'JSON object with address details',
    preferences JSON COMMENT 'Customer preferences as JSON',
    metadata JSON COMMENT 'Additional customer metadata',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    -- Generated columns from JSON
    city VARCHAR(100) GENERATED ALWAYS AS (JSON_UNQUOTE(JSON_EXTRACT(address, '$.city'))) STORED,
    country VARCHAR(100) GENERATED ALWAYS AS (JSON_UNQUOTE(JSON_EXTRACT(address, '$.country'))) STORED,
    -- Check that address has required fields
    CHECK (JSON_CONTAINS_PATH(address, 'one', '$.street', '$.city', '$.postal_code', '$.country'))
);

-- Create products table with JSON for attributes and options
CREATE TABLE products (
    product_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    base_price DECIMAL(10, 2) NOT NULL,
    attributes JSON COMMENT 'Product attributes as JSON',
    options JSON COMMENT 'Available product options as JSON array',
    dimensions JSON COMMENT 'Product dimensions (width, height, depth)',
    tags JSON COMMENT 'Array of product tags',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    -- Generated columns from JSON
    weight DECIMAL(8, 2) GENERATED ALWAYS AS (JSON_EXTRACT(attributes, '$.weight')) STORED,
    category VARCHAR(50) GENERATED ALWAYS AS (JSON_UNQUOTE(JSON_EXTRACT(attributes, '$.category'))) STORED,
    -- Check that attributes has required fields
    CHECK (JSON_CONTAINS_PATH(attributes, 'one', '$.weight', '$.category'))
);

-- Create orders table with JSON for shipping details
CREATE TABLE orders (
    order_id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    order_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'pending',
    shipping_address JSON NOT NULL COMMENT 'Shipping address as JSON',
    billing_address JSON NOT NULL COMMENT 'Billing address as JSON',
    payment_details JSON COMMENT 'Payment information as JSON',
    shipping_details JSON COMMENT 'Shipping information as JSON',
    metadata JSON COMMENT 'Additional order metadata',
    total_amount DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    -- Generated columns from JSON
    shipping_country VARCHAR(100) GENERATED ALWAYS AS (JSON_UNQUOTE(JSON_EXTRACT(shipping_address, '$.country'))) STORED,
    payment_method VARCHAR(50) GENERATED ALWAYS AS (JSON_UNQUOTE(JSON_EXTRACT(payment_details, '$.method'))) STORED,
    -- Check that addresses have required fields
    CHECK (JSON_CONTAINS_PATH(shipping_address, 'one', '$.street', '$.city', '$.postal_code', '$.country')),
    CHECK (JSON_CONTAINS_PATH(billing_address, 'one', '$.street', '$.city', '$.postal_code', '$.country'))
);

-- Create order_items table with JSON for product configuration
CREATE TABLE order_items (
    order_item_id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    selected_options JSON COMMENT 'Selected product options as JSON',
    custom_attributes JSON COMMENT 'Custom product attributes for this order',
    metadata JSON COMMENT 'Additional item metadata',
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id),
    -- Check constraints
    CHECK (quantity > 0),
    CHECK (unit_price >= 0)
);

-- Create product_reviews table with JSON for review details
CREATE TABLE product_reviews (
    review_id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    customer_id INT NOT NULL,
    rating INT NOT NULL,
    review_text TEXT,
    review_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    helpful_votes INT DEFAULT 0,
    review_details JSON COMMENT 'Additional review details as JSON',
    response JSON COMMENT 'Seller response to review as JSON',
    FOREIGN KEY (product_id) REFERENCES products(product_id),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    -- Check constraints
    CHECK (rating BETWEEN 1 AND 5),
    CHECK (helpful_votes >= 0)
);

-- Insert sample data
INSERT INTO customers (name, email, phone, address, preferences)
VALUES (
    'John Doe',
    'john@example.com',
    '555-123-4567',
    '{"street": "123 Main St", "city": "New York", "postal_code": "10001", "country": "USA"}',
    '{"marketing_emails": true, "theme": "dark", "language": "en-US"}'
);

INSERT INTO products (name, description, base_price, attributes, options, tags)
VALUES (
    'Smartphone X',
    'Latest smartphone with advanced features',
    999.99,
    '{"weight": 180.5, "category": "Electronics", "color": "black", "material": "aluminum"}',
    '[{"name": "storage", "values": ["64GB", "128GB", "256GB"]}, {"name": "color", "values": ["black", "silver", "gold"]}]',
    '["smartphone", "electronics", "5G", "camera"]'
);
