from telegram import Update
from telegram.ext import ContextTypes
from bot.keyboards.main_menu import get_main_menu
from bot.database.database import get_connection
import logging
import mysql.connector

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        user = update.effective_user
        if not user:
            await update.message.reply_text("Ошибка: пользователь не распознан")
            return

        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()

            # Явное создание таблицы (на случай проблем с миграциями)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS clients (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    telegram_id BIGINT UNIQUE NOT NULL,
                    full_name VARCHAR(255) NOT NULL,
                    username VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Вставка данных
            cursor.execute(
                "INSERT INTO clients (telegram_id, full_name, username) "
                "VALUES (%s, %s, %s) "
                "ON DUPLICATE KEY UPDATE full_name = VALUES(full_name), username = VALUES(username)",
                (user.id, user.full_name, user.username or '')
            )
            conn.commit()

        except mysql.connector.Error as err:
            logger.error(f"MySQL error: {err}")
            await update.message.reply_text("Ошибка базы данных. Код: " + str(err.errno))
            return

        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

        welcome_text = (
            f"👋 Привет, {user.full_name}!\n"
            "Я бот для записи на прием. Вот что я умею:\n\n"
            "📅 Записаться на прием\n"
            "📋 Посмотреть свои записи\n"
            "❌ Отменить запись"
        )

        await update.message.reply_text(
            welcome_text,
            reply_markup=get_main_menu()
        )

    except Exception as e:
        logger.error(f"Error in /start: {e}")
        await update.message.reply_text("Произошла внутренняя ошибка 😢")

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "ℹ️ Помощь по боту:\n\n"
        "📅 Записаться - выбрать время приема\n"
        "📋 Мои записи - просмотр активных записей\n"
        "❌ Отменить - удалить существующую запись",
        reply_markup=get_main_menu()
    )