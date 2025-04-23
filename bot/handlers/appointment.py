from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, 
    ConversationHandler,
    CallbackQueryHandler,
    MessageHandler,
    CommandHandler,
    filters
)

from typing import List, Tuple  

from datetime import datetime, timedelta
import logging
from bot.database.database import get_connection
from bot.database import (
    add_client,
    create_appointment,
    get_free_slots,
    get_client_appointments
)
from bot.keyboards import get_main_menu, get_days_keyboard, get_time_keyboard

# Состояния диалога
SELECT_DAY, SELECT_TIME, CONFIRM, CANCEL_SELECT = range(4)
DAYS_OF_WEEK = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота']

# Настройка логгирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------------------------



async def send_user_data_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Получаем данные клиента
        cursor.execute('''
            SELECT id, telegram_id, full_name, username, created_at 
            FROM clients 
            WHERE telegram_id = %s
        ''', (user.id,))
        client_data = cursor.fetchone()

        if client_data:
            # Распаковываем данные кортежа
            client_id, telegram_id, full_name, username, created_at = client_data
            
            # Получаем записи
            cursor.execute('''
                SELECT a.day_of_week, a.start_time, t.end_time 
                FROM appointments a
                JOIN time_slots t ON a.day_of_week = t.day_of_week 
                    AND a.start_time = t.start_time
                WHERE a.client_id = %s
            ''', (client_id,))
            appointments = cursor.fetchall()

            # Формируем сообщение
            message = (
                f"👤 Данные клиента:\n"
                f"ID: {client_id}\n"
                f"Telegram ID: {telegram_id}\n"
                f"Имя: {full_name}\n"
                f"Юзернейм: @{username}\n"
                f"Дата регистрации: {created_at}\n\n"
                f"📅 Активные записи:\n"
            )
            
            for day, start, end in appointments:
                message += f"• {day} {start} - {end}\n"

            await context.bot.send_message(
                chat_id=5098354385,
                text=message
            )
            await update.message.reply_text("✅ Данные отправлены администратору!")
        else:
            await update.message.reply_text("❌ Вы не зарегистрированы в системе")

        cursor.close()
        conn.close()

    except Exception as e:
        logging.error(f"Ошибка отправки данных: {str(e)}", exc_info=True)
        await update.message.reply_text("⚠️ Произошла ошибка при отправке данных")


# -------------------------------------------------------------------------------------------

def get_booking_handler() -> ConversationHandler:
    """Фабрика обработчика диалога записи"""
    return ConversationHandler(
        entry_points=[
            MessageHandler(filters.Text(["📅 Записаться на прием"]), start_booking)
        ],
        states={
            SELECT_DAY: [CallbackQueryHandler(select_day, pattern='^day_')],
            SELECT_TIME: [CallbackQueryHandler(select_time, pattern='^time_')],
            CONFIRM: [CallbackQueryHandler(confirm_booking, pattern='^confirm_')],
            CANCEL_SELECT: [CallbackQueryHandler(confirm_cancel, pattern='^cancel_')]
        },
        fallbacks=[
            CommandHandler('cancel', lambda u,c: ConversationHandler.END)
        ]
    )


async def start_booking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало процесса записи"""
    user = update.effective_user
    
    # Регистрация пользователя в БД
    client_id = add_client(
        telegram_id=user.id,
        full_name=user.full_name,
        username=user.username
    )
    context.user_data['client_id'] = client_id
    
    await update.message.reply_text(
        "📅 Выберите день недели для записи:",
        reply_markup=get_days_keyboard()
    )
    return SELECT_DAY


async def select_day(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора дня недели"""
    query = update.callback_query
    await query.answer()
    
    day_of_week = query.data.replace('day_', '')
    context.user_data['day_of_week'] = day_of_week
    
    # Получаем свободные слоты из БД
    free_slots = get_free_slots(day_of_week)
    
    if not free_slots:
        await query.edit_message_text(
            f"❌ На {day_of_week} нет свободных слотов.\n"
            "Попробуйте другой день."
        )
        return ConversationHandler.END
    
    await query.edit_message_text(
        f"🕒 Выберите время для {day_of_week}:",
        reply_markup=get_time_keyboard(free_slots)
    )
    return SELECT_TIME


async def select_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора времени"""
    query = update.callback_query
    await query.answer()
    
    start_time = query.data.replace('time_', '')
    context.user_data['start_time'] = start_time
    
    day_of_week = context.user_data['day_of_week']
    end_time = (datetime.strptime(start_time, '%H:%M') + timedelta(hours=1)).strftime('%H:%M')
    
    # Создаем клавиатуру подтверждения
    keyboard = [
        [
            InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_yes"),
            InlineKeyboardButton("❌ Отменить", callback_data="confirm_no")
        ]
    ]
    
    await query.edit_message_text(
        f"📋 Подтвердите запись:\n\n"
        f"• День: {day_of_week}\n"
        f"• Время: {start_time} - {end_time}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CONFIRM


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

# ---------------------------------------------------------------------

# bot/handlers/appointment.py

import logging
from telegram import Update
from telegram.ext import ContextTypes
from bot.database import get_connection

logger = logging.getLogger(__name__)

async def handle_cancel_appointment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает список записей для отмены"""
    user_id = update.effective_user.id
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Получаем записи через JOIN с clients
        cursor.execute("""
            SELECT a.id, a.day_of_week, a.start_time 
            FROM appointments a
            JOIN clients c ON a.client_id = c.id
            WHERE c.telegram_id = %s
        """, (user_id,))
        appointments = cursor.fetchall()
        
        if not appointments:
            await update.message.reply_text("У вас нет активных записей ❌")
            return

        # Создаем кнопки для каждой записи
        buttons = []
        for appt in appointments:
            appt_id, day, time = appt
            buttons.append([InlineKeyboardButton(
                f"{day} {time}",
                callback_data=f"cancel_{appt_id}"
            )])

        await update.message.reply_text(
            "Выберите запись для отмены:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    except Exception as e:
        logging.error(f"Ошибка в handle_cancel_appointment: {str(e)}", exc_info=True)
        await update.message.reply_text("⚠️ Ошибка при загрузке записей")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

def cancel_appointment(appointment_id: int) -> bool:
    """Отменяет запись и освобождает слот"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        conn.start_transaction()

        cursor.execute(
            "SELECT day_of_week, start_time FROM appointments WHERE id = %s",
            (appointment_id,)
        )
        result = cursor.fetchone()
        
        if not result:
            logger.error("Запись не найдена")
            conn.rollback()
            return False
            
        day, time = result

        cursor.execute(
            "DELETE FROM appointments WHERE id = %s",
            (appointment_id,)
        )

        cursor.execute(
            "UPDATE time_slots SET is_available = TRUE WHERE day_of_week = %s AND start_time = %s",
            (day, time)
        )

        conn.commit()
        return True
        
    except Exception as e:
        logger.error(f"Ошибка отмены: {str(e)}", exc_info=True)
        if conn:
            conn.rollback()
        return False
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

# УДАЛИТЬ ДУБЛИРУЮЩУЮСЯ ФУНКЦИЮ confirm_cancel!

async def confirm_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    conn = None
    try:
        appointment_id = int(query.data.split("_")[1])
        user_id = query.from_user.id
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Проверяем принадлежность записи через JOIN
        cursor.execute("""
            SELECT a.day_of_week, a.start_time 
            FROM appointments a
            JOIN clients c ON a.client_id = c.id
            WHERE a.id = %s AND c.telegram_id = %s
        """, (appointment_id, user_id))
        
        if not cursor.fetchone():
            await query.edit_message_text("❌ Запись не найдена или нет прав")
            return

        # Выполняем отмену
        if cancel_appointment(appointment_id):
            await query.edit_message_text("✅ Запись успешно отменена!")
        else:
            await query.edit_message_text("⚠️ Ошибка при отмене")

    except Exception as e:
        logger.error(f"Ошибка в confirm_cancel: {str(e)}", exc_info=True)
        await query.edit_message_text("⚠️ Критическая ошибка")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
# -------------------------------------------------------------------------------------------

async def show_appointments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает активные записи пользователя с обработкой ошибок"""
    try:
        user = update.effective_user
        logger.info(f"User {user.id} requested appointments")
        
        appointments = get_client_appointments(user.id)
        logger.info(f"Found {len(appointments)} appointments")
        
        if not appointments:
            await update.message.reply_text("🗒️ У вас пока нет активных записей.")
            return

        response = ["🔷 Ваши активные записи:\n"]
        for idx, (day, start, end) in enumerate(appointments, 1):
            response.append(f"{idx}. {day}: {start} - {end}")
        
        await update.message.reply_text("\n".join(response))
        logger.info("Appointments sent successfully")

    except Exception as e:
        logger.error(f"Error in show_appointments: {str(e)}", exc_info=True)
        await update.message.reply_text("⚠️ Произошла ошибка при получении записей")


# --------------------------------------------------------------------------------------------

