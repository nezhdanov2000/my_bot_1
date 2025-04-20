import mysql.connector
from dotenv import load_dotenv
from pathlib import Path
import os
from typing import List, Tuple, Optional
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
    """Добавляет или обновляет клиента, возвращает ID"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Вставка с обработкой дублей
        cursor.execute(
            "INSERT INTO clients (telegram_id, full_name, username) "
            "VALUES (%s, %s, %s) "
            "ON DUPLICATE KEY UPDATE full_name = VALUES(full_name), username = VALUES(username)",
            (telegram_id, full_name, username)
        )
        
        # Всегда получаем актуальный ID клиента
        cursor.execute(
            "SELECT id FROM clients WHERE telegram_id = %s",
            (telegram_id,)
        )
        client_id = cursor.fetchone()[0]
        
        conn.commit()
        return client_id
        
    except Exception as e:
        logging.error(f"Ошибка добавления клиента: {str(e)}")
        return None
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

# В файле appointment.py добавьте проверку client_id:

async def start_booking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    
    client_id = add_client(user.id, user.full_name, user.username)
    
    if not client_id:
        await update.message.reply_text("❌ Ошибка регистрации. Попробуйте позже.")
        return ConversationHandler.END
    
    context.user_data['client_id'] = client_id
    logger.info(f"Успешная регистрация: client_id={client_id}")  # Добавьте это

# -------------------------
# Функции для работы с записями
# -------------------------

def create_appointment(client_id: int, day: str, time: str) -> bool:
    """Создает новую запись с блокировкой транзакции"""
    conn = None
    try:
        conn = get_connection()
        conn.start_transaction()  # ← Начало транзакции

        cursor = conn.cursor()

        # 1. Проверка слота с блокировкой FOR UPDATE
        cursor.execute(
            "SELECT id FROM time_slots "
            "WHERE day_of_week = %s "
            "AND start_time = %s "
            "AND is_available = TRUE "
            "FOR UPDATE",  # ← Блокируем слот на время транзакции
            (day, time)
        )
        slot = cursor.fetchone()

        if not slot:
            conn.rollback()
            return False

        slot_id = slot[0]

        # 2. Помечаем слот как занятый
        cursor.execute(
            "UPDATE time_slots SET is_available = FALSE WHERE id = %s",
            (slot_id,)
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
        logging.error(f"Ошибка записи: {str(e)}", exc_info=True)
        if conn:
            conn.rollback()
        return False
    finally:
        if conn and conn.is_connected():
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

            # Добавьте логгирование
            logger.info(f"Данные для записи: "
                      f"client_id={client_id}, "
                      f"day={day}, "
                      f"time={time}")
            
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
        cursor = conn.cursor(dictionary=True)  # Используем словарь
        
        # Получаем client_id
        cursor.execute("SELECT id FROM clients WHERE telegram_id = %s", (telegram_id,))
        client = cursor.fetchone()
        if not client:
            return []
            
        # Получаем записи
        cursor.execute("""
            SELECT 
                a.day_of_week,
                DATE_FORMAT(a.start_time, '%H:%i') as start_time,
                DATE_FORMAT(t.end_time, '%H:%i') as end_time
            FROM appointments a
            JOIN time_slots t 
                ON a.day_of_week = t.day_of_week 
                AND a.start_time = t.start_time
            WHERE a.client_id = %s
            ORDER BY FIELD(a.day_of_week, 
                'Понедельник','Вторник','Среда',
                'Четверг','Пятница','Суббота','Воскресенье'),
                a.start_time
        """, (client['id'],))
        
        return [tuple(row.values()) for row in cursor.fetchall()]
        
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        return []
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
