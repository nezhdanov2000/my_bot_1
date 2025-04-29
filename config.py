import os
from pathlib import Path

# Пути
# BASE_DIR = Path(__file__).parent.parent
# DB_NAME = BASE_DIR / "database" / "appointments.db"

# Настройки бота
BOT_TOKEN = "8157057549:AAGBntU0vC1WaVOjNnRRsgAAn3kyFt0P1c8"  # Ваш токен
# ADMIN_CHAT_ID = 123456789  # Ваш chat_id

# Настройки расписания (24/7)
# WORKING_HOURS = [f"{h:02d}:00" for h in range(0, 24)] + [f"{h:02d}:30" for h in range(0, 24)]
# WORKING_DAYS_RANGE = 365  # Год для записи вперед
# TIMEZONE = "Europe/Moscow"

DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'database': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'auth_plugin': 'mysql_native_password'  # Важно для MySQL 8+
}