from telegram import ReplyKeyboardMarkup

def get_main_menu() -> ReplyKeyboardMarkup:
    """Возвращает клавиатуру главного меню"""
    buttons = [
        ["📅 Записаться на прием", "📋 Мои записи"],
        ["❌ Отменить запись", "🆘 Помощь"]
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=False)