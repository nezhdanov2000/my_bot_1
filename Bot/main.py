import logging
from bot.database.database import init_database
from config import BOT_TOKEN
from bot.handlers import common, appointment
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler
)
import logging


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO 
)


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    init_database()

    # Основные команды
    app.add_handler(CommandHandler("start", common.start))
    app.add_handler(CommandHandler("help", common.help))

    # Обработчик записи на прием
    app.add_handler(appointment.get_booking_handler())

    
    # Просмотр записей
    app.add_handler(MessageHandler(
        filters.Text(["📋 Мои записи"]),
        appointment.show_appointments
    ))

    # Отмена записей
    app.add_handler(MessageHandler(
        filters.Text(["❌ Отменить запись"]),
        appointment.cancel_appointment
    ))

    # Помощь
    app.add_handler(MessageHandler(
        filters.Text(["🆘 Помощь"]),
        common.help
    ))
    
    # Обработчик ошибок
    app.add_error_handler(error_handler)

    app.run_polling()


async def error_handler(update, context):
    logging.error(f"Ошибка: {context.error}")
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Произошла ошибка. Пожалуйста, попробуйте позже."
    )


# ----------------------------------------------------------------------------

if __name__ == "__main__":
    main()