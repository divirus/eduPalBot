import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
)
from handlers import (
    start,
    essay,
    essay_type,
    waiting_for_theme,
    essay_result,
    math,
    math_type,
    waiting_for_math_input,
    math_result,
    cancel,
    clear,
    handle_unexpected_input,
    ESSAY_TYPE,
    WAITING_FOR_THEME,
    ESSAY_RESULT,
    MATH_TYPE,
    WAITING_FOR_MATH_INPUT,
    MATH_RESULT,
)
from config import TELEGRAM_TOKEN

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.DEBUG
)
logger = logging.getLogger(__name__)

def main():
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Обработчик команды /start
    application.add_handler(CommandHandler("start", start))

    # ConversationHandler для "Сочинение"
    essay_conv = ConversationHandler(
        entry_points=[
            CommandHandler("essay", essay),
            MessageHandler(
                filters.TEXT & ~filters.COMMAND & filters.Regex(r"^📝\s*Русский\sязык$"),
                essay
            ),
        ],
        states={
            ESSAY_TYPE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    essay_type
                ),
            ],
            WAITING_FOR_THEME: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    waiting_for_theme
                )
            ],
            ESSAY_RESULT: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND & filters.Regex(
                        r"^(🔄\s*Новый\s+запрос|🏠\s*В\s+главное\s+меню)$"
                    ),
                    essay_result
                ),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_unexpected_input),
        ],
    )
    application.add_handler(essay_conv)

    # ConversationHandler для "Математика"
    math_conv = ConversationHandler(
        entry_points=[
            CommandHandler("math", math),
            MessageHandler(
                filters.TEXT & ~filters.COMMAND & filters.Regex(r"^🔢\s*Математика$"),
                math
            ),
        ],
        states={
            MATH_TYPE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    math_type
                ),
            ],
            WAITING_FOR_MATH_INPUT: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    waiting_for_math_input
                )
            ],
            MATH_RESULT: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND & filters.Regex(
                        r"^(🔄\s*Новый\s+запрос|🏠\s*В\s+главное\s+меню)$"
                    ),
                    math_result
                ),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_unexpected_input),
        ],
    )
    application.add_handler(math_conv)

    # Обработчики команд /cancel и /clear
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CommandHandler("clear", clear))

    # Обработчик для неожиданного ввода вне ConversationHandler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_unexpected_input))

    # Запуск бота
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()