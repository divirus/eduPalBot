from telegram import Update, ReplyKeyboardRemove
from telegram.ext import CommandHandler, MessageHandler, ConversationHandler, filters
from keyboards import MAIN_MENU, SECTION_MENU, ESSAY_TYPE_MENU, MATH_MENU
from gigachat.services import retry_query_gigachat
import pypandoc
import logging
import re
import emoji  # Import the emoji library

logger = logging.getLogger(__name__)

# Telegram constants
MAX_MESSAGE_LENGTH = 4000
LOADING_MESSAGE = "Пожалуйста, дождитесь ответа..."

ESSAY_TYPE, WAITING_FOR_THEME, ESSAY_RESULT, EQUATION, MATH_RESULT = range(5)

async def start(update: Update, context):
    user = update.message.from_user.first_name
    welcome_message = (
        f"Привет, {user}! Я бот-помощник для школьников и их родителей.\n"
        "Я помогу написать сочинение, решить пример и объяснить почему он так решается.\n"
        "Чтобы продолжить, выберите раздел ниже:"
    )
    logger.info("Пользователь запустил бота с /start")
    await update.message.reply_text(
        "Инициализация...",
        reply_markup=ReplyKeyboardRemove()
    )
    await update.message.reply_text(
        welcome_message,
        reply_markup=MAIN_MENU
    )
    return ConversationHandler.END

async def essay(update: Update, context):
    logger.info("Пользователь выбрал раздел 'Сочинение'")
    await update.message.reply_text(
        "Выберите тип сочинения:",
        reply_markup=ESSAY_TYPE_MENU,
    )
    return ESSAY_TYPE

async def essay_type(update: Update, context):
    text = update.message.text.strip()
    logger.debug("Получен выбор типа сочинения (длина=%d)", len(text))
    # Remove emoji using the emoji library
    text_no_emoji = emoji.replace_emoji(text, replace='').lower()
    # Normalize whitespace by collapsing consecutive spaces
    text_no_emoji = re.sub(r'\s+', ' ', text_no_emoji).strip()

    if text_no_emoji == "назад":
        logger.info("Пользователь выбрал 'Назад' в essay_type")
        await update.message.reply_text(
            "Возвращаемся в главное меню...",
            reply_markup=ReplyKeyboardRemove()
        )
        await update.message.reply_text(
            "Выберите раздел ниже:",
            reply_markup=MAIN_MENU,
            parse_mode="HTML"
        )
        return ConversationHandler.END

    context.user_data['essay_type'] = text_no_emoji

    if text_no_emoji == "краткое содержание произведения":
        logger.info("Пользователь выбрал 'Краткое содержание произведения'")
        await update.message.reply_text(
            "Пожалуйста, введите автора и название произведения:",
            reply_markup=SECTION_MENU,
            parse_mode="HTML"
        )
    elif text_no_emoji == "сочинение по теме":
        logger.info("Пользователь выбрал 'Сочинение по теме'")
        await update.message.reply_text(
            "Пожалуйста, введите тему сочинения:",
            reply_markup=SECTION_MENU,
            parse_mode="HTML"
        )
    else:
        logger.warning("Получен недопустимый выбор типа сочинения")
        await update.message.reply_text(
            "Недопустимый выбор...",
            reply_markup=ReplyKeyboardRemove()
        )
        await update.message.reply_text(
            "Пожалуйста, выберите <b>📚 Краткое содержание произведения</b>, <b>✍️ Сочинение по теме</b> или <b>🔙 Назад</b>:",
            reply_markup=ESSAY_TYPE_MENU,
            parse_mode="HTML"
        )
        return ESSAY_TYPE
    
    return WAITING_FOR_THEME

async def waiting_for_theme(update: Update, context):
    text = update.message.text.strip()
    text_no_emoji = emoji.replace_emoji(text, replace='').lower()
    text_no_emoji = re.sub(r'\s+', ' ', text_no_emoji).strip()
    logger.debug("Получена тема сочинения (длина=%d)", len(text))

    if text_no_emoji == "в главное меню":
        logger.info("Пользователь выбрал 'В главное меню' в waiting_for_theme")
        await update.message.reply_text(
            "Возвращаемся в главное меню...",
            reply_markup=ReplyKeyboardRemove()
        )
        await update.message.reply_text(
            "Выберите раздел ниже:",
            reply_markup=MAIN_MENU,
            parse_mode="HTML"
        )
        return ConversationHandler.END
    elif text_no_emoji == "новый запрос":
        logger.info("Пользователь выбрал 'Новый запрос' в waiting_for_theme")
        await update.message.reply_text(
            "Выберите тип сочинения...",
            reply_markup=ReplyKeyboardRemove()
        )
        await update.message.reply_text(
            "Выберите тип сочинения:",
            reply_markup=ESSAY_TYPE_MENU,
            parse_mode="HTML"
        )
        return ESSAY_TYPE
    
    context.user_data['essay_theme'] = text

    context.user_data['essay_theme'] = text

    if context.user_data['essay_type'] == "краткое содержание произведения":
        prompt = f"Представь что ты учитель литературы. Напиши сочинение с кратким содержанием произведения '{text}' на русском языке, языком понятным школьнику."
    else:
        prompt = f"Представь что ты учитель литературы. Напиши сочинение на тему '{text}' на русском языке, языком понятным школьнику."

    await update.message.reply_text("Пожалуйста, дождитесь ответа...")
    try:
        response = await retry_query_gigachat(prompt, max_tokens=2048)
        if len(response) > 4000:
            response = response[:4000] + "..."
        await update.message.reply_text(
            f"Сочинение:\n{response}",
            reply_markup=SECTION_MENU
        )
    except Exception as e:
        logger.error("Ошибка при подготовке сочинения (%s)", type(e).__name__)
        await update.message.reply_text(
            "Не удалось получить ответ. Попробуйте ещё раз позже.",
            reply_markup=SECTION_MENU
        )
    return ESSAY_RESULT

async def essay_result(update: Update, context):
    text = update.message.text.strip()
    text_no_emoji = emoji.replace_emoji(text, replace='').lower()
    text_no_emoji = re.sub(r'\s+', ' ', text_no_emoji).strip()

    if text_no_emoji == "новый запрос":
        logger.info("Пользователь выбрал 'Новый запрос' в essay_result")
        await essay(update, context)
        return ESSAY_TYPE
    elif text_no_emoji == "в главное меню":
        logger.info("Пользователь выбрал 'В главное меню' в essay_result")
        await update.message.reply_text(
            "Возвращаемся в главное меню...",
            reply_markup=ReplyKeyboardRemove()
        )
        await update.message.reply_text(
            "Выберите раздел ниже:",
            reply_markup=MAIN_MENU,
            parse_mode="HTML"
        )
        return ConversationHandler.END
    else:
        logger.warning("Получен недопустимый выбор после ответа по литературе")
        await update.message.reply_text(
            "Недопустимый выбор...",
            reply_markup=ReplyKeyboardRemove()
        )
        await update.message.reply_text(
            "Пожалуйста, выберите действие из меню ниже:",
            reply_markup=SECTION_MENU,
            parse_mode="HTML"
        )
    return ESSAY_RESULT

async def math(update: Update, context):
    logger.info("Пользователь выбрал раздел 'Математика'")
    await update.message.reply_text(
        "Напишите условие задачи, уравнение или другое задание, например: 2x = 10",
        reply_markup=MATH_MENU
    )
    return EQUATION

def clean_latex_with_pandoc(text: str) -> str:
    try:
        cleaned_text = pypandoc.convert_text(text, 'plain', format='latex')
        cleaned_text = basic_latex_cleaning(cleaned_text)
        return cleaned_text.strip()
    except Exception as e:
        logger.error("Ошибка преобразования LaTeX через Pandoc (%s)", type(e).__name__)
        return basic_latex_cleaning(text)

def basic_latex_cleaning(text: str) -> str:
    replacements = {
        "^2": "²",
        "^3": "³",
        "^4": "⁴",
        "^5": "⁵",
        "^6": "⁶",
        "^7": "⁷",
        "^8": "⁸",
        "^9": "⁹",
        "^0": "⁰",
        "±": "±",
        "√": "√",
        "\\times": "*",
        "\\cdot": "*",
        "\\frac": "/",
        "\\sqrt": "√",
    }
    cleaned_text = text
    for old, new in replacements.items():
        cleaned_text = cleaned_text.replace(old, new)

    cleaned_text = re.sub(r'\$.*?\$', lambda m: m.group(0)[1:-1], cleaned_text)
    cleaned_text = re.sub(r'\\\[', '', cleaned_text)
    cleaned_text = re.sub(r'\\\]', '', cleaned_text)
    cleaned_text = re.sub(r'\\\(', '', cleaned_text)
    cleaned_text = re.sub(r'\\\)', '', cleaned_text)
    cleaned_text = re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r'\1/\2', cleaned_text)
    cleaned_text = re.sub(r'\\text\{([^}]+)\}', r'\1', cleaned_text)
    cleaned_text = re.sub(r'\\text\{([^}]+)\}/\}{', r'\1/', cleaned_text)
    cleaned_text = re.sub(r'\\sqrt\{([^}]+)\}', r'√(\1)', cleaned_text)
    cleaned_text = re.sub(r'([a-zA-Z])_\{([0-9]),([0-9])\}', lambda m: f"{m.group(1)}₁,₂", cleaned_text)
    cleaned_text = re.sub(r'([a-zA-Z])_([0-9])', lambda m: f"{m.group(1)}{chr(0x2080 + int(m.group(2)))}", cleaned_text)
    cleaned_text = re.sub(r'\\,', ' ', cleaned_text)
    cleaned_text = re.sub(r'/\s*\{([^}]+)\}\s*\{([^}]+)\}', r'\1/\2', cleaned_text)
    cleaned_text = re.sub(r'\\log', 'log', cleaned_text)
    cleaned_text = re.sub(r'\\([a-zA-Z]+)', r'\1', cleaned_text)
    return cleaned_text

def normalize_formatting(text: str) -> str:
    normalized_text = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized_text = re.sub(r"^#+[ \t]*", "", normalized_text, flags=re.MULTILINE)
    normalized_text = re.sub(r"[ \t]+", " ", normalized_text)
    normalized_text = re.sub(r"[ \t]+\n", "\n", normalized_text)
    normalized_text = re.sub(
        r"(?<!\n)(?=Шаг \d+:|Итог:|Ответ:)", "\n\n", normalized_text
    )
    normalized_text = re.sub(r"\n[ \t]*\n+", "\n\n", normalized_text)
    return normalized_text.strip()

async def solve_equation(update: Update, context):
    text = update.message.text.strip()
    text_no_emoji = emoji.replace_emoji(text, replace='').lower()
    text_no_emoji = re.sub(r'\s+', ' ', text_no_emoji).strip()
    logger.debug("Получена математическая задача (длина=%d)", len(text))

    if text_no_emoji == "в главное меню":
        logger.info("Пользователь выбрал 'В главное меню' в solve_equation")
        await update.message.reply_text(
            "Возвращаемся в главное меню...",
            reply_markup=ReplyKeyboardRemove()
        )
        await update.message.reply_text(
            "Выберите раздел ниже:",
            reply_markup=MAIN_MENU
        )
        return ConversationHandler.END

    await update.message.reply_text(LOADING_MESSAGE)

    prompt = (
        f"Представь, что ты учитель математики, объясняющий задачу школьнику. "
        f"Реши уравнение или задачу '{text}' и подробно опиши процесс решения на русском языке. "
        f"Используй только простой текст, без любых математических команд (например, $, \\frac, \\sqrt, \\text, \\times, \\cdot, \\[, \\]). "
        f"Пиши дроби как числитель/знаменатель (например, 21/7). "
        f"Пиши умножение как * (например, 3*4). "
        f"Пиши логарифмы как log с основанием в виде нижнего индекса (например, log2(x) вместо log_2(x)). "
        f"Пиши степени через ^ (например, 2^3). "
        f"Пиши единицы измерения (например, кг) как обычный текст после чисел с пробелом. "
        f"Нумеруй шаги как 'Шаг 1:', 'Шаг 2:' и так далее. "
        f"Каждый шаг должен быть отделён пустой строкой (добавляй \n\n между шагами). "
        f"Если есть итог, пиши его как 'Итог:' в конце, тоже отделяя пустой строкой. "
        f"Если указываешь ответ, пиши его как 'Ответ:' на новой строке после 'Итог:'."
    )
    
    try:
        response = await retry_query_gigachat(prompt, max_tokens=2048)
        if not response:
            logger.error("Получен пустой ответ от GigaChat")
            await update.message.reply_text(
                "Произошла ошибка при получении ответа. Попробуйте снова.",
                reply_markup=SECTION_MENU
            )
            return MATH_RESULT
    except Exception as e:
        logger.error("Ошибка при запросе к GigaChat (%s)", type(e).__name__)
        await update.message.reply_text(
            "Произошла ошибка при обработке запроса. Попробуйте снова.",
            reply_markup=SECTION_MENU
        )
        return MATH_RESULT

    logger.debug("Получен ответ GigaChat (длина=%d)", len(response))

    cleaned_response = clean_latex_with_pandoc(response)
    logger.debug("Очищен LaTeX (длина=%d)", len(cleaned_response))

    normalized_response = normalize_formatting(cleaned_response)
    logger.debug("Нормализовано форматирование (длина=%d)", len(normalized_response))

    if len(normalized_response) > MAX_MESSAGE_LENGTH:
        normalized_response = normalized_response[:MAX_MESSAGE_LENGTH] + "..."
        logger.warning("Ответ обрезан из-за превышения лимита Telegram")

    try:
        await update.message.reply_text(
            f"Объяснение:\n{normalized_response}\nЕсли непонятно, уточни!",
            reply_markup=SECTION_MENU
        )
    except Exception as e:
        logger.error("Ошибка при отправке ответа в Telegram (%s)", type(e).__name__)
        await update.message.reply_text(
            "Произошла ошибка при отправке ответа. Попробуйте снова.",
            reply_markup=SECTION_MENU
        )

    return MATH_RESULT

async def math_result(update: Update, context):
    text = update.message.text.strip()
    text_no_emoji = emoji.replace_emoji(text, replace='').lower()
    text_no_emoji = re.sub(r'\s+', ' ', text_no_emoji).strip()

    if text_no_emoji == "новый запрос":
        logger.info("Пользователь выбрал 'Новый запрос' в math_result")
        await math(update, context)
        return EQUATION
    elif text_no_emoji == "в главное меню":
        logger.info("Пользователь выбрал 'В главное меню' в math_result")
        await update.message.reply_text(
            "Возвращаемся в главное меню...",
            reply_markup=ReplyKeyboardRemove()
        )
        await update.message.reply_text(
            "Выберите раздел ниже:",
            reply_markup=MAIN_MENU,
            parse_mode="HTML"
        )
        return ConversationHandler.END
    else:
        logger.warning("Получен недопустимый выбор после ответа по математике")
        await update.message.reply_text(
            "Недопустимый выбор...",
            reply_markup=ReplyKeyboardRemove()
        )
        await update.message.reply_text(
            "Пожалуйста, выберите действие из меню ниже:",
            reply_markup=SECTION_MENU,
            parse_mode="HTML"
        )
    return MATH_RESULT

async def cancel(update: Update, context):
    logger.info("Пользователь вызвал команду /cancel")
    await update.message.reply_text(
        "Если что — пишите снова...",
        reply_markup=ReplyKeyboardRemove()
    )
    await update.message.reply_text(
        "Выберите раздел ниже:",
        reply_markup=MAIN_MENU,
    )
    return ConversationHandler.END

async def clear(update: Update, context):
    logger.info("Пользователь вызвал команду /clear")
    context.user_data.clear()
    await update.message.reply_text(
        "История очищена...",
        reply_markup=ReplyKeyboardRemove()
    )
    await update.message.reply_text(
        "Выберите раздел ниже:",
        reply_markup=MAIN_MENU
    )
    return ConversationHandler.END

async def handle_unexpected_input(update: Update, context):
    text = update.message.text
    logger.warning("Получен текст вне активного сценария")
    await update.message.reply_text(
        "Недопустимый ввод...",
        reply_markup=ReplyKeyboardRemove()
    )
    await update.message.reply_text(
        "Пожалуйста, выберите действие из меню ниже:",
        reply_markup=MAIN_MENU,
        parse_mode="HTML"
    )
    return ConversationHandler.END
