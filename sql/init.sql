-- FileWallBall Database Initialization
-- This file is used to initialize the MariaDB database for FileWallBall

-- Create database if not exists (though docker compose already does this)
CREATE DATABASE IF NOT EXISTS filewallball_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Grant privileges to user (docker compose already creates the user)
GRANT ALL PRIVILEGES ON filewallball_db.* TO 'filewallball_user'@'%';
FLUSH PRIVILEGES;

USE filewallball_db;

-- Basic table structure will be created by Alembic migrations
-- This file ensures the database is ready for the application