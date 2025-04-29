from telegram import Update, ReplyKeyboardRemove
from telegram.ext import CommandHandler, MessageHandler, ConversationHandler, filters
from keyboards import MAIN_MENU, SECTION_MENU, ESSAY_TYPE_MENU, MATH_TYPE_MENU
from services import retry_query_gigachat
import pypandoc
import logging
import re
import emoji
from payment import is_subscribed, can_make_request, increment_request_count, get_remaining_requests, FREE_REQUESTS_LIMIT

logger = logging.getLogger(__name__)

# Константы для Telegram
MAX_MESSAGE_LENGTH = 4000
LOADING_MESSAGE = "Пожалуйста, дождитесь ответа..."
FINAL_MESSAGE_TEMPLATE = "Объяснение:\n<pre>{}</pre>\nЕсли непонятно, уточни!"
SELECT_ACTION_MESSAGE = "Выберите действие ниже:"

# Глобальные константы для сообщений
WELCOME_MESSAGE = (
    "Привет, {user}! Я бот-помощник для школьников и их родителей.\n"
    "Я помогу написать сочинение, решить пример и объяснить почему он так решается.\n"
    "У вас есть {free_requests} бесплатных запроса в день. Для безлимитных запросов оформите подписку.\n"
    "Чтобы продолжить, выберите раздел ниже:"
)
INVALID_CHOICE_MESSAGE = "Недопустимый выбор..."
SELECT_ACTION_MESSAGE = "Пожалуйста, выберите действие из меню ниже:"
REQUEST_LIMIT_MESSAGE = (
    "Вы исчерпали лимит бесплатных запросов на сегодня ({limit} запроса в день). "
    "Для безлимитных запросов оформите подписку, выбрав 'Subscribe' в главном меню."
)

ESSAY_TYPE, WAITING_FOR_THEME, ESSAY_RESULT, MATH_TYPE, WAITING_FOR_MATH_INPUT, MATH_RESULT = range(6)

async def start(update: Update, context):
    user_id = update.effective_user.id
    user = update.message.from_user.first_name
    welcome_message = WELCOME_MESSAGE.format(user=user, free_requests=FREE_REQUESTS_LIMIT)
    logger.info("Пользователь запустил бота с /start")

    await update.message.reply_text(
        "Инициализация...",
        reply_markup=ReplyKeyboardRemove()
    )
    await update.message.reply_text(
        welcome_message,
        reply_markup=MAIN_MENU,
        parse_mode="HTML"
    )
    return ConversationHandler.END

def normalize_text(text):
    text_no_emoji = emoji.replace_emoji(text, replace='')  # Удаляем эмодзи
    text_no_emoji = re.sub(r'\s+', ' ', text_no_emoji).strip().lower()  # Убираем лишние пробелы и приводим к нижнему регистру
    return text_no_emoji

async def handle_menu_choice(update, context, text_no_emoji, menu_type):
    logger.info(f"Обработка выбора меню: text_no_emoji='{text_no_emoji}', menu_type='{menu_type}'")
    if text_no_emoji == "новый запрос":
        if menu_type == "essay":
            await essay(update, context)
            return ESSAY_TYPE
        elif menu_type == "math":
            await math(update, context)
            return MATH_TYPE
    elif text_no_emoji == "в главное меню":
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
        logger.warning(f"Недопустимый выбор: '{text_no_emoji}'")
        await update.message.reply_text(
            "Недопустимый выбор...",
            reply_markup=ReplyKeyboardRemove()
        )
        await update.message.reply_text(
            "Выберите действие ниже:",
            reply_markup=SECTION_MENU,
            parse_mode="HTML"
        )
        return menu_type
    
def format_response(response):
    """
    Processes a response by removing LaTeX, Markdown, and formatting it for Telegram.
    
    Args:
        response (str): The raw response text.
    
    Returns:
        str: Formatted text suitable for Telegram with HTML tags.
    """
    if not response or not isinstance(response, str):
        return "Ответ пустой или некорректный."

    # Экранирование специальных символов для Telegram
    response = response.replace('&', '&').replace('<', '<').replace('>', '>')

    # Remove Markdown headers (e.g., ### Header, ## Header, # Header)
    response = re.sub(r'^\s*#{1,3}\s*(.*?)\s*$', r'\1', response, flags=re.MULTILINE)

    # Remove Markdown bold (**text**) and italic (*text*)
    response = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', response)  # Convert **text** to <b>text</b>
    response = re.sub(r'\*(.*?)\*', r'\1', response)  # Remove *text* (italic)

    # Remove LaTeX delimiters
    response = re.sub(r'\$\$?(.*?)\$\$?', r'\1', response)  # Remove $...$ and $$...$$
    response = re.sub(r'\\\[', '', response)  # Remove \[
    response = re.sub(r'\\\]', '', response)  # Remove \]
    response = re.sub(r'\\\(', '', response)  # Remove \(
    response = re.sub(r'\\\)', '', response)  # Remove \)
    
    # Replace LaTeX commands with text equivalents
    response = re.sub(r'\\frac\{(.*?)\}\{(.*?)\}', r'\1/\2', response)  # Fractions: \frac{a}{b} → a/b
    response = re.sub(r'\\sqrt\{(.*?)\}', r'√(\1)', response)  # Roots: \sqrt{a} → √(a)
    response = re.sub(r'\\times', '*', response)  # Multiplication: \times → *
    response = re.sub(r'\\cdot', '*', response)  # Multiplication: \cdot → *
    response = re.sub(r'\\approx', '≈', response)  # Approximately: \approx → ≈
    response = re.sub(r'\\pi', 'π', response)  # Pi: \pi → π
    response = re.sub(r'\\leq', '≤', response)  # Less than or equal: \leq → ≤
    response = re.sub(r'\\geq', '≥', response)  # Greater than or equal: \geq → ≥
    response = re.sub(r'\\sum', 'сумма', response)  # Sum: \sum → сумма
    response = re.sub(r'\\int', 'интеграл', response)  # Integral: \int → интеграл
    response = re.sub(r'\\text\{(.*?)\}', r'\1', response)  # Remove \text{...}
    response = re.sub(r'\\mathrm\{(.*?)\}', r'\1', response)  # Remove \mathrm{...}
    
    # Replace superscripts and subscripts
    response = re.sub(r'\^2', '²', response)  # Square: ^2 → ²
    response = re.sub(r'\^3', '³', response)  # Cube: ^3 → ³
    response = re.sub(r'\^\{(.*?)\}', r'^(\1)', response)  # General powers: ^{n} → ^(n)
    response = re.sub(r'_\{(.*?)\}', r'_(\1)', response)  # Subscripts: _{n} → _(n)
    
    # Apply HTML formatting for structure
    response = re.sub(r'(Шаг \d+:)', r'<b>\1</b>', response)  # Bold "Шаг 1:"
    response = re.sub(r'(Итог:)', r'<b>\1</b>', response)  # Bold "Итог:"
    response = re.sub(r'(Ответ:)', r'<b>\1</b>', response)  # Bold "Ответ:"
    response = re.sub(r'(Задание:)', r'<b>\1</b>', response)  # Bold "Задание:"
    response = re.sub(r'(Решение:)', r'<b>\1</b>', response)  # Bold "Решение:"
    
    # Normalize multiple newlines to a single double newline
    response = re.sub(r'\n\s*\n+', '\n\n', response)
    
    # Remove leading and trailing newlines
    response = response.strip('\n')
    
    return response

async def essay_result(update, context):
    text = update.message.text.strip()
    text_no_emoji = normalize_text(text)
    logger.info(f"essay_result: Получен текст='{text}', нормализованный текст='{text_no_emoji}'")
    return await handle_menu_choice(update, context, text_no_emoji, "essay")

async def math_result(update, context):
    text = update.message.text.strip()
    text_no_emoji = normalize_text(text)
    logger.info(f"math_result: Получен текст='{text}', нормализованный текст='{text_no_emoji}'")
    return await handle_menu_choice(update, context, text_no_emoji, "math")

async def essay(update: Update, context):
    user_id = update.effective_user.id
    if not can_make_request(user_id, context):
        remaining = get_remaining_requests(user_id, context)
        await update.message.reply_text(
            REQUEST_LIMIT_MESSAGE.format(limit=FREE_REQUESTS_LIMIT)
        )
        return ConversationHandler.END
    logger.info("Пользователь выбрал раздел 'Русский язык'")
    await update.message.reply_text(
        "Выберите тип сочинения:",
        reply_markup=ESSAY_TYPE_MENU,
    )
    return ESSAY_TYPE

async def essay_type(update: Update, context):
    text = update.message.text.strip()
    text_no_emoji = emoji.replace_emoji(text, replace='').lower()
    text_no_emoji = re.sub(r'\s+', ' ', text_no_emoji).strip()

    if text_no_emoji == "назад":
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

    if text_no_emoji == "объяснить правила":
        await update.message.reply_text(
            "Пожалуйста, опишите, что требуется объяснить:",
            reply_markup=SECTION_MENU,
            parse_mode="HTML"
        )
    elif text_no_emoji == "написать сочинение":
        await update.message.reply_text(
            "Пожалуйста, введите тему сочинения:",
            reply_markup=SECTION_MENU,
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            INVALID_CHOICE_MESSAGE,
            reply_markup=ReplyKeyboardRemove()
        )
        await update.message.reply_text(
            "Пожалуйста, выберите <b>📚 Объяснить правила</b>, <b>✍️ Написать сочинение</b> или <b>🔙 Назад</b>:",
            reply_markup=ESSAY_TYPE_MENU,
            parse_mode="HTML"
        )
        return ESSAY_TYPE

    return WAITING_FOR_THEME

async def waiting_for_theme(update: Update, context):
    text = update.message.text.strip()
    text_no_emoji = emoji.replace_emoji(text, replace='').lower()
    text_no_emoji = re.sub(r'\s+', ' ', text_no_emoji).strip()

    if text_no_emoji == "в главное меню":
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

    if context.user_data['essay_type'] == "объяснить правила":
        prompt = f"Представь что ты учитель русского языка. Объясни следующие правила '{text}' на русском языке, так чтобы это понял даже ребенок, простыми словами, не используя жаргон и ненормативную лексику."
    else:
        prompt = f"Представь что ты ученик средней школы. Напиши сочинение на тему '{text}' на русском языке, грамотно, языком понятным школьнику, не используя жаргон и ненормативную лексику, минимум 1000 символов."

    prompt += " Пожалуйста, не используй никакие специальные символы для форматирования, такие как **, а дай ответ в простом текстовом виде."
    success = await send_api_request(update, context, prompt)
    if success:
        return ESSAY_RESULT
    return ConversationHandler.END

async def math(update: Update, context):
    user_id = update.effective_user.id
    if not can_make_request(user_id, context):
        remaining = get_remaining_requests(user_id, context)
        await update.message.reply_text(
            REQUEST_LIMIT_MESSAGE.format(limit=FREE_REQUESTS_LIMIT)
        )
        return ConversationHandler.END
    logger.info("Пользователь выбрал раздел 'Математика'")
    await update.message.reply_text(
        "Выберите тип запроса:",
        reply_markup=MATH_TYPE_MENU,
        parse_mode="HTML"
    )
    return MATH_TYPE

async def math_type(update: Update, context):
    text = update.message.text.strip()
    text_no_emoji = emoji.replace_emoji(text, replace='').lower()
    text_no_emoji = re.sub(r'\s+', ' ', text_no_emoji).strip()

    if text_no_emoji == "назад":
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

    context.user_data['math_type'] = text_no_emoji

    if text_no_emoji == "объяснить решение":
        await update.message.reply_text(
            "Введите правило или пример, объяснение которого вы бы хотели получить:",
            reply_markup=SECTION_MENU,
            parse_mode="HTML"
        )
    elif text_no_emoji == "решебник":
        await update.message.reply_text(
            "Введите пример, результат решения которого вы хотели бы получить:",
            reply_markup=SECTION_MENU,
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            INVALID_CHOICE_MESSAGE,
            reply_markup=ReplyKeyboardRemove()
        )
        await update.message.reply_text(
            "Пожалуйста, выберите <b>📚 Объяснить решение</b>, <b>📖 Решебник</b> или <b>🔙 Назад</b>:",
            reply_markup=MATH_TYPE_MENU,
            parse_mode="HTML"
        )
        return MATH_TYPE

    return WAITING_FOR_MATH_INPUT

async def waiting_for_math_input(update: Update, context):
    text = update.message.text.strip()
    text_no_emoji = emoji.replace_emoji(text, replace='').lower()
    text_no_emoji = re.sub(r'\s+', ' ', text_no_emoji).strip()

    if text_no_emoji == "в главное меню":
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
        await update.message.reply_text(
            "Выберите тип запроса...",
            reply_markup=ReplyKeyboardRemove()
        )
        await update.message.reply_text(
            "Выберите тип запроса:",
            reply_markup=MATH_TYPE_MENU,
            parse_mode="HTML"
        )
        return MATH_TYPE

    # Если ввод не является командой меню, отправляем запрос на сервер
    math_type = context.user_data.get('math_type')
    if math_type == "объяснить решение":
        prompt = (
            f"Представь, что ты учитель математики, который должен объяснить ребенку учебный материал. "
            f"Объясни подробно следующее '{text}' на русском языке простыми словами понятными школьнику. "
        )
    else:  # math_type == "решебник"
        prompt = (
            f"Представь, что ты учитель математики, реши задание по математике '{text}' и предоставь результат на русском языке, используй только программу средней школы, не использую материалы из высшей математики. "
        )

    prompt += (
        f"Не дублируй задание в тексте ответа"
        f"Используй только простой текст, НИ В КОЕМ СЛУЧАЕ НЕ ИСПОЛЬЗУЙ LaTeX, математические команды или символы (например, $, \\frac, \\sqrt, \\text, \\times, \\cdot, \\[, \\], \\int)."
        f"Пиши дроби как числитель/знаменатель (например, 21/7). "
        f"Пиши умножение как * (например, 3*4). "
        f"Пиши логарифмы как log с основанием в виде нижнего индекса (например, log2(x) вместо log_2(x)). "
        f"Пиши степени через ^ (например, 2^3). "
        f"Пиши единицы измерения (например, кг) как обычный текст после чисел с пробелом. "
        f"Нумеруй шаги как 'Шаг 1:', 'Шаг 2:' и так далее. "
        f"Каждый шаг должен быть отделён пустой строкой (добавляй \n\n между шагами). "
        f"Если есть итог, пиши его как 'Итог:' в конце, тоже отделяя пустой строкой. "
        f"Если указываешь ответ, пиши его как 'Ответ:' на новой строке после 'Итог:'. "
        f"Перед тем как отправить ответ, убедись что даешь правдивую информацию"
    )

    success = await send_api_request(update, context, prompt)
    if success:
        return MATH_RESULT
    return ConversationHandler.END

async def send_api_request(update: Update, context, prompt):
    user_id = update.effective_user.id
    if not can_make_request(user_id, context):
        remaining = get_remaining_requests(user_id, context)
        await update.message.reply_text(
            REQUEST_LIMIT_MESSAGE.format(limit=FREE_REQUESTS_LIMIT)
        )
        return False

    increment_request_count(user_id, context)
    remaining = get_remaining_requests(user_id, context)
    if remaining is not None:
        await update.message.reply_text(f"Осталось бесплатных запросов на сегодня: {remaining}")

    await update.message.reply_text("Пожалуйста, дождитесь ответа...")
    try:
        response = await retry_query_gigachat(prompt, max_tokens=2048)
        if len(response) > 4000:
            response = response[:4000] + "..."
        formatted_response = format_response(response)
        await update.message.reply_text(
            f"Ответ:\n{formatted_response}",
            reply_markup=SECTION_MENU,
            parse_mode="HTML"
        )
        return True
    except Exception as e:
        await update.message.reply_text(
            f"Произошла ошибка при запросе к GigaChat: {str(e)}",
            reply_markup=SECTION_MENU
        )
        return False

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
    logger.warning(f"Неожиданный ввод текста: '{text}'")
    await update.message.reply_text(
        INVALID_CHOICE_MESSAGE,
        reply_markup=ReplyKeyboardRemove()
    )
    await update.message.reply_text(
        SELECT_ACTION_MESSAGE,
        reply_markup=MAIN_MENU,
        parse_mode="HTML"
    )
    return ConversationHandler.END