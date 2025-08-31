-- FileWallBall Database Initialization Script
-- This script creates the database schema and initial data

-- Create database if not exists
CREATE DATABASE IF NOT EXISTS filewallball_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Use the database
USE filewallball_db;

-- Create projects table
CREATE TABLE IF NOT EXISTS projects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_name VARCHAR(255) NOT NULL UNIQUE,
    project_key VARCHAR(64) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    INDEX idx_project_key (project_key),
    INDEX idx_project_name (project_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create files table
CREATE TABLE IF NOT EXISTS files (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    file_uuid VARCHAR(36) NOT NULL UNIQUE,
    original_filename VARCHAR(255) NOT NULL,
    stored_filename VARCHAR(255) NOT NULL,
    file_extension VARCHAR(20) NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    file_size BIGINT NOT NULL,
    file_hash VARCHAR(64),
    storage_path VARCHAR(500) NOT NULL,
    file_category_id SMALLINT,
    owner_id INT,
    project_key_id INT,
    is_public BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_file_uuid (file_uuid),
    INDEX idx_original_filename (original_filename),
    INDEX idx_file_extension (file_extension),
    INDEX idx_mime_type (mime_type),
    INDEX idx_file_size (file_size),
    INDEX idx_file_hash (file_hash),
    INDEX idx_is_deleted (is_deleted),
    INDEX idx_created_at (created_at),
    INDEX idx_updated_at (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create project_files table (for project-file relationships)
CREATE TABLE IF NOT EXISTS project_files (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    file_id VARCHAR(36) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (file_id) REFERENCES files(file_uuid) ON DELETE CASCADE,
    UNIQUE KEY unique_project_file (project_id, file_id),
    INDEX idx_project_id (project_id),
    INDEX idx_file_id (file_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insert default project for testing
INSERT IGNORE INTO projects (project_name, project_key) VALUES 
('default', 'default-project-key-12345');

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_files_created_at_desc ON files(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_files_original_filename_asc ON files(original_filename ASC);
CREATE INDEX IF NOT EXISTS idx_files_file_size_asc ON files(file_size ASC);

-- Grant permissions to application user
GRANT ALL PRIVILEGES ON filewallball_db.* TO 'filewallball'@'%';
FLUSH PRIVILEGES;
