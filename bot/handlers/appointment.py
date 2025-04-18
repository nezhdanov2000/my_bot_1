from bot.keyboards.main_menu import get_main_menu
from bot.database.database import get_connection
from telegram.ext import CallbackContext
from telegram.ext import ConversationHandler
from telegram import Update
from datetime import datetime, timedelta





def confirm_booking(update: Update, context: CallbackContext) -> int:
    if update.message.text.lower() == 'подтверждаю':
        update.message.reply_text(
            "✅ Запись успешно создана!",
            reply_markup=get_main_menu()
        )
    else:
        update.message.reply_text(
            "❌ Запись отменена",
            reply_markup=get_main_menu()
        )
    return ConversationHandler.END

def start_booking(update: Update, context: CallbackContext) -> int:
    update.message.reply_text(
        "Выберите услугу:",
        reply_markup=get_main_menu()
    )
    return True

def create_appointment(user_id: int, date_str: str, time_str: str):
    """
    Сохраняет запись в базу данных.

    :param user_id: Telegram user ID
    :param date_str: Дата в формате 'YYYY-MM-DD'
    :param time_str: Время в формате 'HH:MM'
    """
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        INSERT INTO appointments (user_id, appointment_date, appointment_time)
        VALUES (%s, %s, %s)
    """
    cursor.execute(query, (user_id, date_str, time_str))
    conn.commit()

    cursor.close()
    conn.close()

def show_appointments(update: Update, context: CallbackContext) -> int:
    update.message.reply_text(
        "Выберите услугу:",
        reply_markup=get_main_menu()
    )
    return True

def cancel_appointment(update: Update, context: CallbackContext) -> int:
    update.message.reply_text(
        "Выберите услугу:",
        reply_markup=get_main_menu()
    )
    return True


