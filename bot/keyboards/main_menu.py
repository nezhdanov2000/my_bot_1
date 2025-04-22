from telegram import ReplyKeyboardMarkup

def get_main_menu():
    return ReplyKeyboardMarkup(
        [
            ['📅 Записаться на прием', '📋 Мои записи'],
            ['❌ Отменить запись', '🆘 Помощь']
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )