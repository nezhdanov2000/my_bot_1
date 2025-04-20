-- Удаляем старую версию базы если нужно
-- DROP DATABASE IF EXISTS bot_database;

-- Создаем базу заново
CREATE DATABASE bot_database 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE bot_database;

CREATE TABLE IF NOT EXISTS clients (
    id INT AUTO_INCREMENT PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    username VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS time_slots (
    id INT AUTO_INCREMENT PRIMARY KEY,
    day_of_week VARCHAR(20) NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    is_available BOOLEAN DEFAULT TRUE,
    UNIQUE KEY unique_slot (day_of_week, start_time)
);

CREATE TABLE IF NOT EXISTS appointments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    client_id INT NOT NULL,
    day_of_week VARCHAR(20) NOT NULL,
    start_time TIME NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (client_id) REFERENCES clients(id),
    FOREIGN KEY (day_of_week, start_time) REFERENCES time_slots(day_of_week, start_time)
);

-- Только DML-запросы без SELECT
INSERT INTO time_slots (day_of_week, start_time, end_time) VALUES
('Понедельник', '09:00:00', '10:00:00'),
('Понедельник', '10:00:00', '11:00:00'),
('Вторник', '14:00:00', '15:00:00');