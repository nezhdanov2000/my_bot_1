# В файле common.py
from telegram import Update
from telegram.ext import ContextTypes
from telegram.ext import CallbackContext
from bot.keyboards.main_menu import get_main_menu

async def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    welcome_text = (
        f"👋 Привет, {user.first_name}!\n"
        "Я бот для записи на прием. Вот что я умею:\n"
        "📅 - Записаться на прием\n"
        "📋 - Посмотреть свои записи\n"
        "❌ - Отменить запись"
    )
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_menu()
    )

def help(update: Update, context: CallbackContext) -> int:
    update.message.reply_text(
        "Выберите услугу:",
        reply_markup=get_main_menu()
    )
    return True


