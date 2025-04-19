import logging
from config import BOT_TOKEN
from bot.handlers import common, appointment
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters
)


# Логирование
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO 
)

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Базовые команды из common.py
    app.add_handler(CommandHandler("start", common.start))

    # Обработчики кнопок меню
    app.add_handler(MessageHandler(filters.Text(["📅 Записаться на прием"]), appointment.start_booking))
    app.add_handler(MessageHandler(filters.Text(["📋 Мои записи"]), appointment.show_appointments))
    app.add_handler(MessageHandler(filters.Text(["❌ Отменить запись"]), appointment.cancel_appointment))
    app.add_handler(MessageHandler(filters.Text(["🆘 Помощь"]), common.help))
    









    # Я не знаю, что это за обработчик, но он нужен
    app.run_polling()










if __name__ == "__main__":
    main()