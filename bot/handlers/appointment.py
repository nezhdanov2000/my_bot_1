from bot.keyboards.main_menu import get_main_menu
from telegram.ext import CallbackContext
from telegram.ext import ConversationHandler
from telegram import Update
from bot.database import (
    create_appointment,
    get_available_slots,
    get_user_appointments,
    cancel_appointment
)
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














from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from bot.database import (
    add_client,
    create_appointment,
    get_free_slots,
    get_client_appointments
)

# Состояния диалога
SELECT_DAY, SELECT_TIME, CONFIRM = range(3)
DAYS_OF_WEEK = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

async def start_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало процесса записи"""
    user = update.effective_user
    # Регистрируем/получаем клиента
    client_id = add_client(
        telegram_id=user.id,
        full_name=user.full_name,
        username=user.username
    )
    
    context.user_data['client_id'] = client_id
    
    # Создаём клавиатуру с днями недели
    keyboard = [
        [InlineKeyboardButton(day, callback_data=f"day_{day}")]
        for day in DAYS_OF_WEEK
    ]
    
    await update.message.reply_text(
        "📅 Выберите день недели для записи:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return SELECT_DAY

async def select_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора дня недели"""
    query = update.callback_query
    await query.answer()
    
    day_of_week = query.data.replace('day_', '')
    context.user_data['day_of_week'] = day_of_week
    
    # Получаем свободные слоты
    free_slots = get_free_slots(day_of_week)
    
    if not free_slots:
        await query.edit_message_text(
            f"❌ На {day_of_week} нет свободных слотов.\n"
            "Попробуйте другой день."
        )
        return ConversationHandler.END
    
    # Создаём клавиатуру со свободными слотами
    keyboard = [
        [InlineKeyboardButton(slot, callback_data=f"time_{slot}")]
        for slot in free_slots
    ]
    
    await query.edit_message_text(
        f"🕒 Выберите время для {day_of_week}:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return SELECT_TIME

async def select_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора времени"""
    query = update.callback_query
    await query.answer()
    
    start_time = query.data.replace('time_', '')
    context.user_data['start_time'] = start_time
    
    day_of_week = context.user_data['day_of_week']
    end_time = (datetime.strptime(start_time, '%H:%M') + timedelta(hours=1)).strftime('%H:%M')
    
    await query.edit_message_text(
        f"📋 Подтвердите запись:\n\n"
        f"• День: {day_of_week}\n"
        f"• Время: {start_time} - {end_time}\n\n"
        "Нажмите /confirm для подтверждения или /cancel для отмены"
    )
    
    return CONFIRM

async def confirm_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Финальное подтверждение записи"""
    if update.message.text == '/confirm':
        client_id = context.user_data['client_id']
        day_of_week = context.user_data['day_of_week']
        start_time = context.user_data['start_time']
        
        if create_appointment(client_id, day_of_week, start_time):
            await update.message.reply_text(
                "✅ Запись успешно создана!\n\n"
                f"День: {day_of_week}\n"
                f"Время: {start_time} - {(datetime.strptime(start_time, '%H:%M') + timedelta(hours=1)).strftime('%H:%M')}"
            )
        else:
            await update.message.reply_text(
                "❌ Этот слот уже занят. Пожалуйста, начните запись заново."
            )
    else:
        await update.message.reply_text("❌ Запись отменена")
    
    return ConversationHandler.END

async def show_my_appointments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает записи текущего пользователя"""
    telegram_id = update.effective_user.id
    appointments = get_client_appointments(telegram_id)
    
    if not appointments:
        await update.message.reply_text("У вас нет активных записей.")
        return
    
    response = ["Ваши записи:", ""]
    for day, start, end in appointments:
        response.append(f"📌 {day}: {start} - {end}")
    
    await update.message.reply_text("\n".join(response))
