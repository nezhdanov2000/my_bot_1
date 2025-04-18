import logging
from config import BOT_TOKEN
from bot.handlers import common, appointment
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters
)

from telegram.ext import CommandHandler, CallbackQueryHandler
from bot.handlers.appointment import (
    start_booking, select_day, select_time, confirm_booking,
    show_my_appointments
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



        # Обработчик записи
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('book', start_booking)],
        states={
            SELECT_DAY: [CallbackQueryHandler(select_day, pattern='^day_')],
            SELECT_TIME: [CallbackQueryHandler(select_time, pattern='^time_')],
            CONFIRM: [CommandHandler('confirm', confirm_booking)]
        },
        fallbacks=[CommandHandler('cancel', lambda u,c: ConversationHandler.END)]
    )
    
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler('my_appointments', show_my_appointments))
    app.add_handler(CommandHandler('slots', show_free_slots))  # Из предыдущего примера






if __name__ == "__main__":
    main()