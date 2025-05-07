-- Simple schema for testing the MySQL Database Populator
-- This schema includes basic table types with minimal relationships:
-- - Tables with primary keys
-- - Simple foreign key relationships
-- - Basic data types

-- Drop tables if they exist
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS categories;

-- Create categories table
CREATE TABLE categories (
    category_id INT AUTO_INCREMENT PRIMARY KEY,
    category_name VARCHAR(50) NOT NULL,
    description TEXT,
    active BOOLEAN DEFAULT TRUE
);

-- Create products table
CREATE TABLE products (
    product_id INT AUTO_INCREMENT PRIMARY KEY,
    product_name VARCHAR(100) NOT NULL,
    description TEXT,
    price DECIMAL(10, 2) NOT NULL,
    category_id INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(category_id)
);

-- Insert a few records to test with existing data
INSERT INTO categories (category_name, description) 
VALUES ('Electronics', 'Electronic devices and accessories');

INSERT INTO products (product_name, description, price, category_id) 
VALUES ('Smartphone', 'Latest model smartphone', 999.99, 1);
