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


async def confirm_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    appointment_idx = int(query.data.split("_")[1])
    appointments = get_client_appointments(update.effective_user.id)
    
    if appointment_idx >= len(appointments):
        await query.edit_message_text("Ошибка: запись не найдена")
        return
    
    # Получаем ID записи из БД
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT a.id FROM appointments a "
            "JOIN time_slots t ON a.day_of_week = t.day_of_week AND a.start_time = t.start_time "
            "WHERE a.day_of_week = %s AND a.start_time = %s",
            (appointments[appointment_idx][0], appointments[appointment_idx][1]))
        appointment_id = cursor.fetchone()[0]
        
        if cancel_appointment(appointment_id):
            await query.edit_message_text("✅ Запись успешно отменена!")
        else:
            await query.edit_message_text("❌ Ошибка при отмене записи")
            
    except Exception as e:
        logger.error(f"Cancel error: {str(e)}")
        await query.edit_message_text("⚠️ Произошла ошибка")
    finally:
        conn.close()


# ---------------------------------------------------------------------
async def cancel_appointment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало процесса отмены записи"""
    user_id = update.effective_user.id
    
    # Получаем список записей
    appointments = get_client_appointments(user_id)
    
    if not appointments:
        await update.message.reply_text("У вас нет активных записей для отмены.")
        return
    
    # Создаем клавиатуру с записями
    keyboard = [
        [InlineKeyboardButton(
            f"{idx+1}. {day} {start}-{end}", 
            callback_data=f"cancel_{idx}")]
        for idx, (day, start, end) in enumerate(appointments)
    ]
    
    await update.message.reply_text(
        "Выберите запись для отмены:",
        reply_markup=InlineKeyboardMarkup(keyboard))

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

# -------------------------------------------------------------------------------------------

# def create_appointment(client_id: int, day: str, time: str) -> bool:
#     """Создает новую запись"""
#     try:
#         conn = get_connection()
#         cursor = conn.cursor()

#         # 1. Проверка доступности слота
#         cursor.execute(
#             "SELECT id FROM time_slots "
#             "WHERE day_of_week = %s "
#             "AND start_time = %s "
#             "AND is_available = TRUE",
#             (day, time)
#         )
#         slot = cursor.fetchone()
        
#         if not slot:
#             return False

#         # 2. Помечаем слот как занятый
#         cursor.execute(
#             "UPDATE time_slots "
#             "SET is_available = FALSE "
#             "WHERE id = %s",
#             (slot[0],)
#         )

#         # 3. Создаем запись
#         cursor.execute(
#             "INSERT INTO appointments (client_id, day_of_week, start_time) "
#             "VALUES (%s, %s, %s)",
#             (client_id, day, time)
#         )
        
#         conn.commit()
#         return True

#     except Exception as e:
#         logging.error(f"Error creating appointment: {str(e)}")
#         conn.rollback()
#         return False
#     finally:
#         if conn.is_connected():
#             cursor.close()
#             conn.close()



# def get_client_appointments(telegram_id: int) -> List[Tuple]:
#     """Возвращает активные записи клиента"""
#     try:
#         conn = get_connection()
#         cursor = conn.cursor()
        
#         # Получаем client_id по telegram_id
#         cursor.execute(
#             "SELECT id FROM clients WHERE telegram_id = %s",
#             (telegram_id,)
#         )
#         client_id = cursor.fetchone()[0]
        
#         # Получаем записи
#         cursor.execute(
#             "SELECT a.day_of_week, "
#             "TIME_FORMAT(a.start_time, '%H:%i'), "
#             "TIME_FORMAT(t.end_time, '%H:%i') "
#             "FROM appointments a "
#             "JOIN time_slots t ON a.day_of_week = t.day_of_week AND a.start_time = t.start_time "
#             "WHERE a.client_id = %s",
#             (client_id,)
#         )
#         return cursor.fetchall()
        
#     except Exception as e:
#         logging.error(f"Error getting appointments: {e}")
#         return []
#     finally:
#         if conn.is_connected():
#             cursor.close()
#             conn.close()

def cancel_appointment(appointment_id: int) -> bool:
    """Отменяет запись и освобождает слот"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 1. Получаем данные о записи
        cursor.execute(
            "SELECT day_of_week, start_time "
            "FROM appointments WHERE id = %s",
            (appointment_id,)
        )
        day, time = cursor.fetchone()
        
        # 2. Удаляем запись
        cursor.execute(
            "DELETE FROM appointments WHERE id = %s",
            (appointment_id,)
        )
        
        # 3. Освобождаем слот
        cursor.execute(
            "UPDATE time_slots "
            "SET is_available = TRUE "
            "WHERE day_of_week = %s AND start_time = %s",
            (day, time)
        )
        
        conn.commit()
        return True
        
    except Exception as e:
        logging.error(f"Error canceling appointment: {e}")
        return False
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()



