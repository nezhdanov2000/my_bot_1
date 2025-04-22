-- Удаляем старую версию базы если нужно
-- DROP DATABASE IF EXISTS bot_database

-- Создаем базу заново
CREATE DATABASE bot_database 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE bot_database;

-- Создаем таблицу клиентов
CREATE TABLE IF NOT EXISTS clients (
    id INT AUTO_INCREMENT PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    username VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создаем таблицу слотов времени с первичным ключом
CREATE TABLE IF NOT EXISTS time_slots (
    day_of_week VARCHAR(20) NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    is_available BOOLEAN DEFAULT TRUE,
    PRIMARY KEY (day_of_week, start_time)  -- Составной первичный ключ
);

-- Создаем таблицу записей с корректными внешними ключами
CREATE TABLE IF NOT EXISTS appointments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    client_id INT NOT NULL,
    day_of_week VARCHAR(20) NOT NULL,
    start_time TIME NOT NULL,
    FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE,
    FOREIGN KEY (day_of_week, start_time) 
        REFERENCES time_slots(day_of_week, start_time) ON DELETE CASCADE
);

-- Только DML-запросы без SELECT
INSERT INTO time_slots (day_of_week, start_time, end_time)
VALUES 
    ('Понедельник', '09:00', '10:00'),
    ('Понедельник', '10:00', '11:00');