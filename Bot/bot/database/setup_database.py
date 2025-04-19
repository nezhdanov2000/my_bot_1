import mysql.connector
import os

from dotenv import load_dotenv
from pathlib import Path

load_dotenv()  # Загружаем переменные из .env
from config import DB_CONFIG


def init_db():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        sql_path = os.path.join(os.path.dirname(__file__), 'init_database.sql')
        print(f"🔄 Загружаем SQL из: {sql_path}")  # Отладочный вывод
        
        with open(sql_path, 'r', encoding='utf-8') as sql_file:
            sql_commands = sql_file.read().split(';')
            for i, command in enumerate(sql_commands):
                if command.strip():
                    print(f"⚡ Выполняем команду #{i+1}: {command[:50]}...")  # Логируем
                    cursor.execute(command)
        
        conn.commit()
        print("✅ База данных инициализирована!")
        
        # Дополнительная проверка
        cursor.execute("SHOW TABLES")
        print("Созданные таблицы:", cursor.fetchall())
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        if conn.is_connected():
            conn.close()


init_db()