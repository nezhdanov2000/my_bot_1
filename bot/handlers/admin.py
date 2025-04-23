from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters
)
from config import ADMIN_IDS
import mysql.connector
import logging
from datetime import time

from bot.database.database import get_connection

async def show_slots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT day_of_week, start_time, end_time, is_available
            FROM time_slots
            ORDER BY 
                FIELD(day_of_week, 
                    'Понедельник','Вторник','Среда',
                    'Четверг','Пятница','Суббота','Воскресенье'),
                start_time
        ''')
        
        slots = cursor.fetchall()
        message = "📋 Список всех слотов:\n\n"
        for day, start, end, available in slots:
            status = "✅ Свободен" if available else "⛔ Занят"
            start_time = str(start).rjust(5, '0')  # Форматирование времени
            end_time = str(end).rjust(5, '0')
            message += f"🗓 {day}: {start_time} - {end_time} | {status}\n"
            
        if not slots:
            message = "❌ Нет доступных слотов"
            
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message
        )
    except Exception as e:
        logging.error(f"Ошибка при получении слотов: {str(e)}", exc_info=True)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="⚠️ Произошла ошибка при получении данных"
        )
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

# Обновим состояния
SELECT_ACTION, SELECT_DAY, INPUT_TIME, CONFIRM = range(4)

async def admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Доступ запрещен")
        return ConversationHandler.END
        
    keyboard = [
        [InlineKeyboardButton("➕ Добавить слот", callback_data="add_slot")],
        [InlineKeyboardButton("📋 Список слотов", callback_data="list_slots")]
    ]
    await update.message.reply_text(
        "Админ-панель:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return SELECT_ACTION

async def select_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "add_slot":
        days_keyboard = [
            [InlineKeyboardButton("Понедельник", callback_data="day_Понедельник")],
            [InlineKeyboardButton("Вторник", callback_data="day_Вторник")],
            [InlineKeyboardButton("Среда", callback_data="day_Среда")],
            [InlineKeyboardButton("Четверг", callback_data="day_Четверг")],
            [InlineKeyboardButton("Пятница", callback_data="day_Пятница")],
            [InlineKeyboardButton("Суббота", callback_data="day_Суббота")],
            [InlineKeyboardButton("Воскресенье", callback_data="day_Воскресенье")],
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel")]
        ]
        await query.edit_message_text(
            "Выберите день недели:",
            reply_markup=InlineKeyboardMarkup(days_keyboard)
        )
        return SELECT_DAY
    elif query.data == "list_slots":
        await show_slots(update, context)
        return ConversationHandler.END

async def select_day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel":
        await query.edit_message_text("❌ Добавление отменено")
        return ConversationHandler.END
    
    context.user_data['day'] = query.data.split("_")[1]
    await query.edit_message_text(
        f"📅 День: {context.user_data['day']}\n"
        "Введите время начала и окончания в формате ЧЧ:ММ-ЧЧ:ММ\n"
        "Пример: 14:30-16:00"
    )
    return INPUT_TIME

async def input_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    time_input = update.message.text
    try:
        start_str, end_str = time_input.split('-')
        start_time = time.fromisoformat(start_str.strip() + ":00")
        end_time = time.fromisoformat(end_str.strip() + ":00")
        
        context.user_data['start_time'] = start_time
        context.user_data['end_time'] = end_time
        
        confirm_keyboard = [
            [InlineKeyboardButton("✅ Подтвердить", callback_data="confirm")],
            [InlineKeyboardButton("❌ Отменить", callback_data="cancel")]
        ]
        
        await update.message.reply_text(
            f"Проверьте данные:\n"
            f"День: {context.user_data['day']}\n"
            f"Время: {start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}\n"
            "Подтверждаете добавление слота?",
            reply_markup=InlineKeyboardMarkup(confirm_keyboard)
        )
        return CONFIRM
    except Exception as e:
        await update.message.reply_text(
            "❌ Неверный формат. Попробуйте еще раз в формате ЧЧ:ММ-ЧЧ:ММ\n"
            "Пример: 14:30-16:00"
        )
        return INPUT_TIME

async def confirm_slot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "confirm":
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO time_slots 
                (day_of_week, start_time, end_time)
                VALUES (%s, %s, %s)
            ''', (
                context.user_data['day'],
                context.user_data['start_time'].strftime('%H:%M:%S'),
                context.user_data['end_time'].strftime('%H:%M:%S')
            ))
            conn.commit()
            
            await query.edit_message_text("✅ Слот успешно добавлен!")
        except mysql.connector.Error as err:
            await query.edit_message_text(f"❌ Ошибка: {err.msg}")
        finally:
            cursor.close()
            conn.close()
    else:
        await query.edit_message_text("❌ Добавление отменено")
    
    context.user_data.clear()
    return ConversationHandler.END

def get_admin_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("admin", admin_start)],
        states={
            SELECT_ACTION: [CallbackQueryHandler(select_action)],
            SELECT_DAY: [CallbackQueryHandler(select_day)],
            INPUT_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_time)],
            CONFIRM: [CallbackQueryHandler(confirm_slot)]
        },
        fallbacks=[
            CommandHandler("cancel", lambda u,c: ConversationHandler.END),
            MessageHandler(filters.Regex("^❌ Отмена$"), lambda u,c: ConversationHandler.END)
        ],
        allow_reentry=True
    )