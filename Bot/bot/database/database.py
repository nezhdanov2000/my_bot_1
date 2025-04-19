import mysql.connector
from dotenv import load_dotenv
from pathlib import Path
import os
from typing import List, Tuple, Optional
import logging
import logging




from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
import logging

logger = logging.getLogger(__name__)





load_dotenv()

DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'database': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'port': int(os.getenv('DB_PORT', 3306))
}

# -------------------------
# Базовые функции подключения
# -------------------------

def get_connection():
    return mysql.connector.connect(**DB_CONFIG)

def init_database():
    """Инициализирует БД, выполняя SQL-скрипт"""
    try:
        conn = mysql.connector.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            port=DB_CONFIG['port']
        )
        cursor = conn.cursor(buffered=True)  # Добавляем буферизацию

        current_dir = Path(__file__).parent
        sql_file_path = current_dir / 'init_database.sql'

        with open(sql_file_path, 'r', encoding='utf-8') as sql_file:
            sql_commands = sql_file.read().split(';')
            
            for command in sql_commands:
                cleaned_command = command.strip()
                if cleaned_command:
                    try:
                        cursor.execute(cleaned_command)
                        if cursor.with_rows:
                            cursor.fetchall()  # Считываем все результаты
                    except Exception as e:
                        logging.error(f"Error executing command: {cleaned_command[:50]}... | Error: {e}")
                        continue

        conn.commit()
        logging.info("✅ Database initialized successfully!")

    except Exception as e:
        logging.error(f"❌ Database initialization failed: {e}")
        raise
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

# -------------------------
# Функции для работы с клиентами
# -------------------------

def add_client(telegram_id: int, full_name: str, username: str) -> int:
    """Добавляет клиента в БД, возвращает ID клиента"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO clients (telegram_id, full_name, username) "
            "VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE full_name=%s",
            (telegram_id, full_name, username, full_name)
        )
        client_id = cursor.lastrowid
        conn.commit()
        return client_id if client_id else telegram_id
        
    except Exception as e:
        logging.error(f"Error adding client: {e}")
        return telegram_id
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

# -------------------------
# Функции для работы с записями
# -------------------------

def create_appointment(client_id: int, day: str, time: str) -> bool:
    """Создает новую запись"""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # 1. Проверяем доступность слота в time_slots
        cursor.execute(
            "SELECT id FROM time_slots "
            "WHERE day_of_week = %s "
            "AND start_time = %s "
            "AND is_available = TRUE",
            (day, time)
        )
        slot = cursor.fetchone()
        
        if not slot:
            return False

        # 2. Помечаем слот как занятый
        cursor.execute(
            "UPDATE time_slots "
            "SET is_available = FALSE "
            "WHERE id = %s",
            (slot[0],)
        )

        # 3. Создаем запись
        cursor.execute(
            "INSERT INTO appointments (client_id, day_of_week, start_time) "
            "VALUES (%s, %s, %s)",
            (client_id, day, time)
        )
        
        conn.commit()
        return True

    except Exception as e:
        logging.error(f"Error creating appointment: {str(e)}")
        conn.rollback()
        return False
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

async def confirm_booking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Финальное подтверждение записи"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'confirm_yes':
        try:
            client_id = context.user_data['client_id']
            day = context.user_data['day_of_week']
            time = context.user_data['start_time']

            logger.info(f"Attempting to create appointment: {day} {time} for client {client_id}")
            
            if create_appointment(client_id, day, time):
                await query.edit_message_text("✅ Запись успешно создана!")
            else:
                await query.edit_message_text("❌ Этот слот уже занят. Пожалуйста, начните заново.")
        
        except Exception as e:
            logger.error(f"Error in confirmation: {str(e)}")
            await query.edit_message_text("⚠️ Произошла ошибка при создании записи")

    else:
        await query.edit_message_text("❌ Запись отменена")
    
    return ConversationHandler.END

def get_free_slots(day: str) -> List[str]:
    """Возвращает список свободных временных слотов"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Используем TIME_FORMAT для преобразования времени в строку 'HH:MM'
        cursor.execute(
            "SELECT TIME_FORMAT(start_time, '%H:%i') "
            "FROM time_slots "
            "WHERE day_of_week = %s AND is_available = TRUE",
            (day,)
        )
        return [row[0] for row in cursor.fetchall()]
        
    except Exception as e:
        logging.error(f"Error getting slots: {e}")
        return []
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def get_client_appointments(telegram_id: int) -> List[Tuple]:
    """Возвращает активные записи клиента"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT a.day_of_week, a.start_time, t.end_time "
            "FROM appointments a "
            "JOIN time_slots t ON a.day_of_week = t.day_of_week AND a.start_time = t.start_time "
            "WHERE a.client_id = %s",
            (telegram_id,)
        )
        return cursor.fetchall()
        
    except Exception as e:
        logging.error(f"Error getting appointments: {e}")
        return []
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def cancel_appointment(appointment_id: int) -> bool:
    """Отменяет запись по ID"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "DELETE FROM appointments WHERE id = %s",
            (appointment_id,)
        )
        conn.commit()
        return cursor.rowcount > 0
        
    except Exception as e:
        logging.error(f"Error canceling appointment: {e}")
        return False
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


