from telegram import Update
from telegram.ext import ContextTypes
from bot.keyboards import get_days_keyboard  # Ensure this function is defined in bot.keyboards

# Define SELECT_DAY or import it from the appropriate module
SELECT_DAY = "select_day"

async def start_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Получите клавиатуру с днями
    keyboard = get_days_keyboard()  # Предполагается, что функция определена в bot.keyboards
    
    await update.message.reply_text(
        "📅 Выберите день недели для записи:",
        reply_markup=keyboard
    )
    return SELECT_DAY