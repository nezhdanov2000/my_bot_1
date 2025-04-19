from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, 
    ConversationHandler,
    CallbackQueryHandler,
    MessageHandler,
    CommandHandler,
    filters
)
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
SELECT_DAY, SELECT_TIME, CONFIRM = range(3)
DAYS_OF_WEEK = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота']

# Настройка логгирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

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

async def show_appointments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает активные записи пользователя"""
    appointments = get_client_appointments(update.effective_user.id)
    
    if not appointments:
        await update.message.reply_text("У вас нет активных записей.")
        return
    
    response = ["Ваши записи:\n"]
    for idx, (day, start, end) in enumerate(appointments, 1):
        response.append(f"{idx}. {day}: {start} - {end}")
    
    await update.message.reply_text("\n".join(response))

def get_booking_handler() -> ConversationHandler:
    """Фабрика обработчика диалога записи"""
    return ConversationHandler(
        entry_points=[
            MessageHandler(filters.Text(["📅 Записаться на прием"]), start_booking)
        ],
        states={
            SELECT_DAY: [CallbackQueryHandler(select_day, pattern='^day_')],
            SELECT_TIME: [CallbackQueryHandler(select_time, pattern='^time_')],
            CONFIRM: [CallbackQueryHandler(confirm_booking, pattern='^confirm_')]
        },
        fallbacks=[
            CommandHandler('cancel', lambda u,c: ConversationHandler.END)
        ]
    )

async def create_appointment(client_id: int, day: str, time: str) -> bool:
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