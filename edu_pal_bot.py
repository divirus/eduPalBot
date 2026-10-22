import telegram
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ConversationHandler, filters
from telegram import ReplyKeyboardMarkup, KeyboardButton
import logging
from config import TELEGRAM_TOKEN, require_env
from services import retry_query_hugging_face

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def _generate_or_notify_failure(update, prompt, max_length, reply_markup):
    try:
        return await retry_query_hugging_face(prompt, max_length=max_length)
    except Exception as error:
        logger.error("Hugging Face request failed (%s)", type(error).__name__)
        await update.message.reply_text(
            "Не удалось получить ответ. Попробуйте ещё раз позже.",
            reply_markup=reply_markup,
        )
        return None

# Состояния для ConversationHandler
ESSAY_TYPE, ESSAY_THEME, EQUATION, LOGIC = range(4)

# Основное меню
MAIN_MENU = ReplyKeyboardMarkup(
    [[KeyboardButton("Сочинение"), KeyboardButton("Математика"), KeyboardButton("Логика")]],
    resize_keyboard=True
)

SECTION_MENU = ReplyKeyboardMarkup(
    [[KeyboardButton("Новый запрос"), KeyboardButton("В главное меню")]],
    resize_keyboard=True
)

SUBSECTION_MENU = ReplyKeyboardMarkup(
    [[KeyboardButton("Назад"), KeyboardButton("В главное меню")]],
    resize_keyboard=True
)

# Меню для выбора типа сочинения
ESSAY_TYPE_MENU = ReplyKeyboardMarkup(
    [[KeyboardButton("Краткое содержание произведения"), KeyboardButton("Сочинение по теме")],
     [KeyboardButton("Назад")]],
    resize_keyboard=True
)

# Приветствие
async def start(update, context):
    user = update.message.from_user.first_name
    welcome_message = (
        f"Привет, {user}! Я бот-помощник для школьников 1-7 классов и их родителей.\n"
        "Выбери раздел ниже:"
    )
    await update.message.reply_text(welcome_message, reply_markup=MAIN_MENU)
    return ConversationHandler.END

# --- Сочинение ---
async def essay(update, context):
    await update.message.reply_text(
        "Выберите тип сочинения:",
        reply_markup=ESSAY_TYPE_MENU
    )
    return ESSAY_TYPE

async def essay_type(update, context):
    text = update.message.text.lower()
    if text == "назад":
        await update.message.reply_text("Возвращаемся в главное меню!", reply_markup=MAIN_MENU)
        return ConversationHandler.END
    context.user_data['essay_type'] = text
    if text == "краткое содержание произведения":
        await update.message.reply_text(
            "Введите название произведения:",
            reply_markup=SUBSECTION_MENU
        )
    elif text == "сочинение по теме":
        await update.message.reply_text(
            "Введите тему сочинения:",
            reply_markup=SUBSECTION_MENU
        )
    else:
        await update.message.reply_text(
            "Выберите 'Краткое содержание произведения' или 'Сочинение по теме':",
            reply_markup=ESSAY_TYPE_MENU
        )
        return ESSAY_TYPE
    return ESSAY_THEME

async def essay_theme(update, context):
    text = update.message.text.lower()
    if text == "в главное меню":
        await update.message.reply_text("Возвращаемся в главное меню!", reply_markup=MAIN_MENU)
        return ConversationHandler.END
    elif text == "назад":
        await update.message.reply_text(
            "Выберите тип сочинения:",
            reply_markup=ESSAY_TYPE_MENU
        )
        return ESSAY_TYPE
    
    context.user_data['essay_theme'] = text
    # Формируем понятный школьнику промпт
    if context.user_data['essay_type'].lower() == "краткое содержание произведения":
        prompt = f"Напиши краткое содержание произведения '{text}' на русском языке, понятное школьнику."
    else:
        prompt = f"Напиши сочинение на тему '{text}' на русском языке, понятное школьнику."
    
    await update.message.reply_text("Пожалуйста, дождитесь ответа...")
    response = await _generate_or_notify_failure(update, prompt, 150, SECTION_MENU)
    if response is None:
        return ConversationHandler.END
    await update.message.reply_text(
        f"Сочинение:\n{response}",
        reply_markup=SECTION_MENU
    )
    return ConversationHandler.END

# --- Математика ---
async def math(update, context):
    await update.message.reply_text(
        "Напиши уравнение, например: '2x + 3 = 7'.",
        reply_markup=SUBSECTION_MENU
    )
    return EQUATION

async def solve_equation(update, context):
    text = update.message.text.lower()
    if text == "в главное меню":
        await update.message.reply_text("Возвращаемся в главное меню!", reply_markup=MAIN_MENU)
        return ConversationHandler.END
    elif text == "назад":
        await update.message.reply_text(
            "Напиши новое уравнение!",
            reply_markup=SUBSECTION_MENU
        )
        return EQUATION
    
    await update.message.reply_text("Пожалуйста, дождитесь ответа...")
    prompt = f"Реши уравнение '{text}' пошагово на русском языке. Используй простой язык для школьника."
    response = await _generate_or_notify_failure(update, prompt, 200, SECTION_MENU)
    if response is None:
        return ConversationHandler.END
    await update.message.reply_text(
        f"Объяснение:\n{response}\nЕсли непонятно, уточни!",
        reply_markup=SECTION_MENU
    )
    return ConversationHandler.END

# --- Логика ---
async def logic(update, context):
    await update.message.reply_text(
        "Логическая задача: 'У Маши 3 конфеты, у Пети на 2 больше. Сколько у Пети?'\n"
        "Напиши ответ или 'другая' для новой задачи.",
        reply_markup=SUBSECTION_MENU
    )
    return LOGIC

async def solve_logic(update, context):
    text = update.message.text.lower()
    if text == "в главное меню":
        await update.message.reply_text("Возвращаемся в главное меню!", reply_markup=MAIN_MENU)
        return ConversationHandler.END
    elif text == "назад":
        await update.message.reply_text(
            "Логическая задача: 'У Маши 3 конфеты, у Пети на 2 больше. Сколько у Пети?'\n"
            "Напиши ответ или 'другая'.",
            reply_markup=SUBSECTION_MENU
        )
        return LOGIC
    
    if text == "5":
        reply = "Верно! У Пети 5 конфет."
        await update.message.reply_text(reply, reply_markup=SECTION_MENU)
        return ConversationHandler.END
    elif text == "другая":
        await update.message.reply_text("Пожалуйста, дождитесь ответа...")
        prompt = "Придумай простую логическую задачу для школьников 1-7 классов на русском языке."
        new_task = await _generate_or_notify_failure(
            update, prompt, 100, SUBSECTION_MENU
        )
        if new_task is None:
            return LOGIC
        await update.message.reply_text(
            f"Новая задача: {new_task}\nНапиши ответ!",
            reply_markup=SUBSECTION_MENU
        )
        return LOGIC
    else:
        await update.message.reply_text(
            "Подумай еще! Ответ: 5. Попробуй снова или напиши 'другая'.",
            reply_markup=SUBSECTION_MENU
        )
        return LOGIC

# Обработка кнопок главного меню и общих вопросов
async def handle_question(update, context):
    text = update.message.text
    if text == "Сочинение":
        await essay(update, context)
        return ESSAY_TYPE
    elif text == "Математика":
        await math(update, context)
        return EQUATION
    elif text == "Логика":
        await logic(update, context)
        return LOGIC
    elif text == "Новый запрос":
        if "essay_theme" in context.user_data:
            await essay(update, context)
            return ESSAY_TYPE
        elif "equation" in context.user_data:
            await math(update, context)
            return EQUATION
        else:
            await logic(update, context)
            return LOGIC
    elif text == "В главное меню":
        await update.message.reply_text("Возвращаемся в главное меню!", reply_markup=MAIN_MENU)
        return ConversationHandler.END
    else:
        await update.message.reply_text("Пожалуйста, дождитесь ответа...")
        prompt = f"Объясни на русском языке для школьника: {text}"
        response = await _generate_or_notify_failure(
            update, prompt, 150, MAIN_MENU
        )
        if response is None:
            return
        await update.message.reply_text(f"Ответ:\n{response}", reply_markup=MAIN_MENU)

# Отмена
async def cancel(update, context):
    await update.message.reply_text("Если что — пиши снова!", reply_markup=MAIN_MENU)
    return ConversationHandler.END

# Главная функция
def main():
    require_env("TELEGRAM_TOKEN", "HF_API_TOKEN")
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))

    essay_conv = ConversationHandler(
        entry_points=[CommandHandler("essay", essay)],
        states={
            ESSAY_TYPE: [MessageHandler(filters.Text() & ~filters.Command(), essay_type)],
            ESSAY_THEME: [MessageHandler(filters.Text() & ~filters.Command(), essay_theme)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    application.add_handler(essay_conv)

    math_conv = ConversationHandler(
        entry_points=[CommandHandler("math", math)],
        states={EQUATION: [MessageHandler(filters.Text() & ~filters.Command(), solve_equation)]},
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    application.add_handler(math_conv)

    logic_conv = ConversationHandler(
        entry_points=[CommandHandler("logic", logic)],
        states={LOGIC: [MessageHandler(filters.Text() & ~filters.Command(), solve_logic)]},
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    application.add_handler(logic_conv)

    application.add_handler(MessageHandler(filters.Text() & ~filters.Command(), handle_question))

    application.run_polling()

if __name__ == '__main__':
    main()
