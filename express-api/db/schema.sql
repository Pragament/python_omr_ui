/**
 * Multi-Tenant & Multi-School API Schema DDL
 * Supports Strapi-style Users & Permissions with Google OAuth & Multi-School Assignment
 */

-- Create Schools Table
CREATE TABLE IF NOT EXISTS schools (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    code VARCHAR(50) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create Users Table (Google OAuth & Strapi Users-Permissions compatible)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    google_id VARCHAR(255),
    role VARCHAR(50) DEFAULT 'test_editor',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create User-School Assignment Table (Single user can have test_editor role for multiple schools)
CREATE TABLE IF NOT EXISTS user_schools (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    school_id INT REFERENCES schools(id) ON DELETE CASCADE,
    role VARCHAR(50) DEFAULT 'test_editor',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, school_id)
);

-- Create Multi-Tenant Tests Table
CREATE TABLE IF NOT EXISTS tests (
    id SERIAL PRIMARY KEY,
    school_id INT REFERENCES schools(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    date VARCHAR(20) NOT NULL,
    template_folder VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create Multi-Tenant OMR Test Results Table (JSONB for dynamic student score rows)
CREATE TABLE IF NOT EXISTS test_results (
    id SERIAL PRIMARY KEY,
    test_id INT REFERENCES tests(id) ON DELETE CASCADE,
    school_id INT REFERENCES schools(id) ON DELETE CASCADE,
    test_name VARCHAR(255) NOT NULL,
    data JSONB NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sample Data Seeding for Multi-School Testing
INSERT INTO schools (name, code) VALUES 
('Delhi Public School', 'DPS_DELHI'),
('St. Xavier High School', 'STX_MUMBAI'),
('Greenwood International', 'GWI_BLR')
ON CONFLICT (code) DO NOTHING;

INSERT INTO users (email, name, role) VALUES 
('editor@example.com', 'Test Editor User', 'test_editor'),
('teacher@example.com', 'Multi School Teacher', 'test_editor')
ON CONFLICT (email) DO NOTHING;

-- Assign Teacher user to multiple schools with test_editor role
INSERT INTO user_schools (user_id, school_id, role) VALUES 
(1, 1, 'test_editor'),
(1, 2, 'test_editor'),
(2, 1, 'test_editor'),
(2, 2, 'test_editor'),
(2, 3, 'test_editor')
ON CONFLICT DO NOTHING;
