import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
)
from gigachat.handlers import (
    start,
    essay,
    essay_type,
    waiting_for_theme,
    essay_result,
    math,
    solve_equation,
    math_result,
    cancel,
    clear,
    handle_unexpected_input,
    ESSAY_TYPE,
    WAITING_FOR_THEME,
    ESSAY_RESULT,
    EQUATION,
    MATH_RESULT,
)
from config import TELEGRAM_TOKEN, require_env
from keyboards import ESSAY_BUTTON, MATH_BUTTON

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

def main():
    require_env("TELEGRAM_TOKEN", "GIGACHAT_AUTH_KEY")
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    conversation = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("essay", essay),
            MessageHandler(
                filters.TEXT & ~filters.COMMAND & filters.Regex(rf"^{ESSAY_BUTTON}$"),
                essay,
            ),
            CommandHandler("math", math),
            MessageHandler(
                filters.TEXT & ~filters.COMMAND & filters.Regex(rf"^{MATH_BUTTON}$"),
                math,
            ),
        ],
        states={
            ESSAY_TYPE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, essay_type),
            ],
            WAITING_FOR_THEME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, waiting_for_theme),
            ],
            ESSAY_RESULT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, essay_result),
            ],
            EQUATION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, solve_equation),
            ],
            MATH_RESULT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, math_result),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("clear", clear),
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_unexpected_input),
        ],
        allow_reentry=True,
    )
    application.add_handler(conversation)

    # Handlers for the /cancel and /clear commands
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CommandHandler("clear", clear))

    # Handle unexpected input outside ConversationHandler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_unexpected_input))

    # Start the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
