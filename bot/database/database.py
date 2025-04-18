import sqlite3
from datetime import datetime, timedelta

def init_db():
    conn = sqlite3.connect('appointments.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS clients (
        client_id INTEGER PRIMARY KEY,
        telegram_id INTEGER UNIQUE,
        full_name TEXT NOT NULL,
        username TEXT,
        registration_date TEXT DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        day_of_week TEXT CHECK(day_of_week IN ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')),
        start_time TEXT,
        end_time TEXT GENERATED ALWAYS AS (
            time(start_time, '+1 hour')
        ) VIRTUAL,
        FOREIGN KEY (client_id) REFERENCES clients (client_id),
        UNIQUE (day_of_week, start_time)
    ''')
    
    conn.commit()
    conn.close()

init_db()


def add_client(telegram_id, full_name, username=None):
    conn = sqlite3.connect('appointments.db')
    cursor = conn.cursor()
    try:
        cursor.execute('''
        INSERT INTO clients (telegram_id, full_name, username)
        VALUES (?, ?, ?)
        ''', (telegram_id, full_name, username))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        # Пользователь уже существует
        cursor.execute('SELECT client_id FROM clients WHERE telegram_id = ?', (telegram_id,))
        return cursor.fetchone()[0]
    finally:
        conn.close()

def create_appointment(client_id, day_of_week, start_time):
    conn = sqlite3.connect('appointments.db')
    cursor = conn.cursor()
    try:
        cursor.execute('''
        INSERT INTO appointments (client_id, day_of_week, start_time)
        VALUES (?, ?, ?)
        ''', (client_id, day_of_week, start_time))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Слот уже занят
        return False
    finally:
        conn.close()

def get_free_slots(day_of_week):
    """Возвращает свободные часовые слоты на указанный день недели"""
    conn = sqlite3.connect('appointments.db')
    cursor = conn.cursor()
    
    # Все возможные слоты (с 9:00 до 18:00 с шагом в 1 час)
    all_slots = [f"{hour:02d}:00" for hour in range(9, 18)]
    
    # Занятые слоты
    cursor.execute('''
    SELECT start_time FROM appointments
    WHERE day_of_week = ?
    ''', (day_of_week,))
    
    booked_slots = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    return [slot for slot in all_slots if slot not in booked_slots]

def get_client_appointments(telegram_id):
    """Возвращает все записи клиента"""
    conn = sqlite3.connect('appointments.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT a.day_of_week, a.start_time, a.end_time 
    FROM appointments a
    JOIN clients c ON a.client_id = c.client_id
    WHERE c.telegram_id = ?
    ORDER BY a.day_of_week, a.start_time
    ''', (telegram_id,))
    
    appointments = cursor.fetchall()
    conn.close()
    return appointments