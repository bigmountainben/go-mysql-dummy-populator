-- Spatial schema for testing the MySQL Database Populator
-- This schema focuses on spatial data types and operations:
-- - POINT, LINESTRING, POLYGON data types
-- - Spatial indexes
-- - Spatial functions and operators

-- Drop tables if they exist
DROP TABLE IF EXISTS delivery_routes;
DROP TABLE IF EXISTS customer_visits;
DROP TABLE IF EXISTS service_areas;
DROP TABLE IF EXISTS points_of_interest;
DROP TABLE IF EXISTS stores;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS cities;
DROP TABLE IF EXISTS regions;

-- Create regions table with polygon boundaries
CREATE TABLE regions (
    region_id INT AUTO_INCREMENT PRIMARY KEY,
    region_name VARCHAR(100) NOT NULL,
    boundary POLYGON NOT NULL COMMENT 'Polygon representing the region boundary',
    center POINT GENERATED ALWAYS AS (ST_Centroid(boundary)) STORED,
    area DOUBLE GENERATED ALWAYS AS (ST_Area(boundary)) STORED,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    SPATIAL INDEX (boundary)
);

-- Create cities table with point locations
CREATE TABLE cities (
    city_id INT AUTO_INCREMENT PRIMARY KEY,
    city_name VARCHAR(100) NOT NULL,
    region_id INT NOT NULL,
    location POINT NOT NULL COMMENT 'Point representing the city center',
    boundary POLYGON NOT NULL COMMENT 'Polygon representing the city boundary',
    population INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (region_id) REFERENCES regions(region_id),
    SPATIAL INDEX (location),
    SPATIAL INDEX (boundary)
);

-- Create customers table with point locations
CREATE TABLE customers (
    customer_id INT AUTO_INCREMENT PRIMARY KEY,
    customer_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    phone VARCHAR(20),
    location POINT NOT NULL COMMENT 'Point representing the customer location',
    city_id INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (city_id) REFERENCES cities(city_id),
    SPATIAL INDEX (location)
);

-- Create stores table with point locations and service areas
CREATE TABLE stores (
    store_id INT AUTO_INCREMENT PRIMARY KEY,
    store_name VARCHAR(100) NOT NULL,
    location POINT NOT NULL COMMENT 'Point representing the store location',
    city_id INT NOT NULL,
    opening_hours VARCHAR(100),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (city_id) REFERENCES cities(city_id),
    SPATIAL INDEX (location)
);

-- Create points of interest table
CREATE TABLE points_of_interest (
    poi_id INT AUTO_INCREMENT PRIMARY KEY,
    poi_name VARCHAR(100) NOT NULL,
    poi_type VARCHAR(50) NOT NULL,
    location POINT NOT NULL COMMENT 'Point representing the POI location',
    description TEXT,
    city_id INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (city_id) REFERENCES cities(city_id),
    SPATIAL INDEX (location)
);

-- Create service areas table with polygon boundaries
CREATE TABLE service_areas (
    service_area_id INT AUTO_INCREMENT PRIMARY KEY,
    store_id INT NOT NULL,
    boundary POLYGON NOT NULL COMMENT 'Polygon representing the service area',
    service_level VARCHAR(20) NOT NULL COMMENT 'e.g., "standard", "express", "premium"',
    max_delivery_time INT COMMENT 'Maximum delivery time in minutes',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (store_id) REFERENCES stores(store_id),
    SPATIAL INDEX (boundary)
);

-- Create customer visits table with timestamps and locations
CREATE TABLE customer_visits (
    visit_id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    store_id INT NOT NULL,
    visit_time DATETIME NOT NULL,
    entry_point POINT NOT NULL COMMENT 'Point representing where customer entered the store',
    duration_minutes INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (store_id) REFERENCES stores(store_id),
    SPATIAL INDEX (entry_point)
);

-- Create delivery routes table with linestring paths
CREATE TABLE delivery_routes (
    route_id INT AUTO_INCREMENT PRIMARY KEY,
    store_id INT NOT NULL,
    route_path LINESTRING NOT NULL COMMENT 'LineString representing the delivery route',
    route_name VARCHAR(100),
    distance DOUBLE GENERATED ALWAYS AS (ST_Length(route_path)) STORED,
    start_point POINT GENERATED ALWAYS AS (ST_StartPoint(route_path)) STORED,
    end_point POINT GENERATED ALWAYS AS (ST_EndPoint(route_path)) STORED,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (store_id) REFERENCES stores(store_id),
    SPATIAL INDEX (route_path)
);

-- Insert sample data
-- Insert a region (polygon)
INSERT INTO regions (region_name, boundary)
VALUES (
    'North Region',
    ST_GeomFromText('POLYGON((0 0, 0 10, 10 10, 10 0, 0 0))')
);

-- Insert a city (point and polygon)
INSERT INTO cities (city_name, region_id, location, boundary, population)
VALUES (
    'Centerville',
    1,
    ST_GeomFromText('POINT(5 5)'),
    ST_GeomFromText('POLYGON((4 4, 4 6, 6 6, 6 4, 4 4))'),
    50000
);

-- Insert a store (point)
INSERT INTO stores (store_name, location, city_id, opening_hours)
VALUES (
    'Downtown Store',
    ST_GeomFromText('POINT(5.1 5.1)'),
    1,
    'Mon-Fri: 9AM-9PM, Sat-Sun: 10AM-8PM'
);

-- Insert a service area (polygon)
INSERT INTO service_areas (store_id, boundary, service_level, max_delivery_time)
VALUES (
    1,
    ST_GeomFromText('POLYGON((4.5 4.5, 4.5 5.5, 5.5 5.5, 5.5 4.5, 4.5 4.5))'),
    'standard',
    30
);

-- Insert a delivery route (linestring)
INSERT INTO delivery_routes (store_id, route_path, route_name)
VALUES (
    1,
    ST_GeomFromText('LINESTRING(5.1 5.1, 5.2 5.2, 5.3 5.1, 5.4 5.2, 5.5 5.0)'),
    'Route A'
);
