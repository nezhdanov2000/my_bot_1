from telegram import InlineKeyboardButton, InlineKeyboardMarkup

DAYS_OF_WEEK = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"]

def get_days_keyboard():
    buttons = [
        [InlineKeyboardButton(day, callback_data=f"day_{day}")]
        for day in DAYS_OF_WEEK
    ]
    return InlineKeyboardMarkup(buttons)

def get_time_keyboard(slots):
    buttons = [
        [InlineKeyboardButton(slot, callback_data=f"time_{slot}")]
        for slot in slots
    ]
    return InlineKeyboardMarkup(buttons)