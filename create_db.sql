
CREATE DATABASE IF NOT EXISTS dms_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;


CREATE USER IF NOT EXISTS 'dms_user'@'localhost'
    IDENTIFIED BY 'your_strong_password_here';

GRANT ALL PRIVILEGES ON dms_db.* TO 'dms_user'@'localhost';

FLUSH PRIVILEGES;

SHOW DATABASES LIKE 'dms_db';
SELECT User, Host FROM mysql.user WHERE User = 'dms_user';
