-- ─────────────────────────────────────────────────────────────────
-- create_db.sql
-- Run with: mysql -u root -p < create_db.sql
-- ─────────────────────────────────────────────────────────────────

-- Create the database with full Unicode support
CREATE DATABASE IF NOT EXISTS dms_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

-- Create a dedicated user (change the password!)
CREATE USER IF NOT EXISTS 'dms_user'@'localhost'
    IDENTIFIED BY 'your_strong_password_here';

-- Grant all privileges on the dms_db database
GRANT ALL PRIVILEGES ON dms_db.* TO 'dms_user'@'localhost';

-- Apply privilege changes
FLUSH PRIVILEGES;

-- Verify
SHOW DATABASES LIKE 'dms_db';
SELECT User, Host FROM mysql.user WHERE User = 'dms_user';
