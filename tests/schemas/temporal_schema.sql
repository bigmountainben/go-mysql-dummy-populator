-- Temporal schema for testing the MySQL Database Populator
-- This schema focuses on temporal data types and operations:
-- - Various date and time data types
-- - Temporal constraints
-- - Historical tracking tables

-- Drop tables if they exist
DROP TABLE IF EXISTS event_attendees;
DROP TABLE IF EXISTS events;
DROP TABLE IF EXISTS appointment_history;
DROP TABLE IF EXISTS appointments;
DROP TABLE IF EXISTS schedule_exceptions;
DROP TABLE IF EXISTS schedules;
DROP TABLE IF EXISTS employee_history;
DROP TABLE IF EXISTS employees;
DROP TABLE IF EXISTS departments;

-- Create departments table
CREATE TABLE departments (
    department_id INT AUTO_INCREMENT PRIMARY KEY,
    department_name VARCHAR(100) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Create employees table
CREATE TABLE employees (
    employee_id INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    hire_date DATE NOT NULL,
    termination_date DATE,
    department_id INT,
    manager_id INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (department_id) REFERENCES departments(department_id),
    FOREIGN KEY (manager_id) REFERENCES employees(employee_id),
    CHECK (termination_date IS NULL OR termination_date >= hire_date)
);

-- Create employee_history table for tracking changes
CREATE TABLE employee_history (
    history_id INT AUTO_INCREMENT PRIMARY KEY,
    employee_id INT NOT NULL,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) NOT NULL,
    hire_date DATE NOT NULL,
    termination_date DATE,
    department_id INT,
    manager_id INT,
    change_date DATETIME NOT NULL,
    change_type ENUM('INSERT', 'UPDATE', 'DELETE') NOT NULL,
    changed_by VARCHAR(100),
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
);

-- Create schedules table
CREATE TABLE schedules (
    schedule_id INT AUTO_INCREMENT PRIMARY KEY,
    employee_id INT NOT NULL,
    day_of_week ENUM('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday') NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    effective_from DATE NOT NULL,
    effective_to DATE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id),
    CHECK (end_time > start_time),
    CHECK (effective_to IS NULL OR effective_to > effective_from)
);

-- Create schedule_exceptions table
CREATE TABLE schedule_exceptions (
    exception_id INT AUTO_INCREMENT PRIMARY KEY,
    employee_id INT NOT NULL,
    exception_date DATE NOT NULL,
    is_working BOOLEAN NOT NULL,
    start_time TIME,
    end_time TIME,
    reason VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id),
    CHECK (is_working = 0 OR (start_time IS NOT NULL AND end_time IS NOT NULL AND end_time > start_time))
);

-- Create appointments table
CREATE TABLE appointments (
    appointment_id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(100) NOT NULL,
    description TEXT,
    start_datetime DATETIME NOT NULL,
    end_datetime DATETIME NOT NULL,
    employee_id INT NOT NULL,
    client_name VARCHAR(100) NOT NULL,
    client_email VARCHAR(100),
    client_phone VARCHAR(20),
    status ENUM('scheduled', 'confirmed', 'cancelled', 'completed') DEFAULT 'scheduled',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id),
    CHECK (end_datetime > start_datetime)
);

-- Create appointment_history table
CREATE TABLE appointment_history (
    history_id INT AUTO_INCREMENT PRIMARY KEY,
    appointment_id INT NOT NULL,
    title VARCHAR(100) NOT NULL,
    description TEXT,
    start_datetime DATETIME NOT NULL,
    end_datetime DATETIME NOT NULL,
    employee_id INT NOT NULL,
    client_name VARCHAR(100) NOT NULL,
    client_email VARCHAR(100),
    client_phone VARCHAR(20),
    status ENUM('scheduled', 'confirmed', 'cancelled', 'completed'),
    change_date DATETIME NOT NULL,
    change_type ENUM('INSERT', 'UPDATE', 'DELETE') NOT NULL,
    changed_by VARCHAR(100),
    FOREIGN KEY (appointment_id) REFERENCES appointments(appointment_id)
);

-- Create events table
CREATE TABLE events (
    event_id INT AUTO_INCREMENT PRIMARY KEY,
    event_name VARCHAR(100) NOT NULL,
    description TEXT,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    start_time TIME,
    end_time TIME,
    is_all_day BOOLEAN DEFAULT FALSE,
    recurrence_pattern VARCHAR(50),
    recurrence_end_date DATE,
    location VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CHECK (end_date >= start_date),
    CHECK (is_all_day = 1 OR (start_time IS NOT NULL AND end_time IS NOT NULL AND end_time > start_time)),
    CHECK (recurrence_pattern IS NULL OR recurrence_end_date IS NOT NULL),
    CHECK (recurrence_end_date IS NULL OR recurrence_end_date >= end_date)
);

-- Create event_attendees table
CREATE TABLE event_attendees (
    event_id INT NOT NULL,
    employee_id INT NOT NULL,
    response_status ENUM('pending', 'accepted', 'declined', 'tentative') DEFAULT 'pending',
    response_date DATETIME,
    PRIMARY KEY (event_id, employee_id),
    FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE,
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
);

-- Insert initial data
INSERT INTO departments (department_name) VALUES ('Human Resources');
INSERT INTO departments (department_name) VALUES ('Engineering');

INSERT INTO employees (first_name, last_name, email, hire_date, department_id, manager_id)
VALUES ('John', 'Smith', 'john.smith@example.com', '2020-01-15', 1, NULL);

INSERT INTO employees (first_name, last_name, email, hire_date, department_id, manager_id)
VALUES ('Jane', 'Doe', 'jane.doe@example.com', '2020-03-01', 2, 1);
