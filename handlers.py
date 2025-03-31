from telegram import Update, ReplyKeyboardRemove
from telegram.ext import CommandHandler, MessageHandler, ConversationHandler, filters
from keyboards import MAIN_MENU, SECTION_MENU, ESSAY_TYPE_MENU, MATH_MENU
from services import retry_query_gigachat
import pypandoc
import logging
import re
import emoji
from payment import is_subscribed, can_make_request, increment_request_count, get_remaining_requests

logger = logging.getLogger(__name__)

# Константы для Telegram
MAX_MESSAGE_LENGTH = 4000
LOADING_MESSAGE = "Пожалуйста, дождитесь ответа..."
FINAL_MESSAGE_TEMPLATE = "Объяснение:\n<pre>{}</pre>\nЕсли непонятно, уточни!"

ESSAY_TYPE, WAITING_FOR_THEME, ESSAY_RESULT, EQUATION, MATH_RESULT = range(5)

async def start(update: Update, context):
    user_id = update.effective_user.id
    user = update.message.from_user.first_name
    welcome_message = (
        f"Привет, {user}! Я бот-помощник для школьников и их родителей.\n"
        "Я помогу написать сочинение, решить пример и объяснить почему он так решается.\n"
        "У вас есть 3 бесплатных запроса в день. Для безлимитных запросов оформите подписку.\n"
        "Чтобы продолжить, выберите раздел ниже:"
    )
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

async def essay(update: Update, context):
    user_id = update.effective_user.id
    if not can_make_request(user_id, context):
        remaining = get_remaining_requests(user_id, context)
        await update.message.reply_text(
            "Вы исчерпали лимит бесплатных запросов на сегодня (3 запроса в день). "
            "Для безлимитных запросов оформите подписку, выбрав 'Subscribe' в главном меню."
        )
        return
    logger.info("Пользователь выбрал раздел 'Сочинение'")
    await update.message.reply_text(
        "Выберите тип сочинения:",
        reply_markup=ESSAY_TYPE_MENU,
    )
    return ESSAY_TYPE

async def essay_type(update: Update, context):
    text = update.message.text.strip()
    logger.info(f"essay_type: Сырой текст: '{text}' (длина: {len(text)})")
    text_no_emoji = emoji.replace_emoji(text, replace='').lower()
    text_no_emoji = re.sub(r'\s+', ' ', text_no_emoji).strip()
    logger.info(f"essay_type: Текст без эмодзи: '{text_no_emoji}' (длина: {len(text_no_emoji)})")

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
        logger.warning(f"Недопустимый ввод в essay_type: '{text}'")
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
    user_id = update.effective_user.id
    text = update.message.text.strip()
    text_no_emoji = emoji.replace_emoji(text, replace='').lower()
    text_no_emoji = re.sub(r'\s+', ' ', text_no_emoji).strip()

    logger.info(f"waiting_for_theme: Получен текст '{text}', без эмодзи: '{text_no_emoji}'")

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
    
    # Увеличиваем счётчик запросов перед выполнением
    increment_request_count(user_id, context)
    remaining = get_remaining_requests(user_id, context)
    if remaining is not None:
        await update.message.reply_text(f"Осталось бесплатных запросов на сегодня: {remaining}")

    context.user_data['essay_theme'] = text

    logger.info(f"Сохранение темы: '{text}'")
    context.user_data['essay_theme'] = text

    if context.user_data['essay_type'] == "краткое содержание произведения":
        prompt = f"Представь что ты учитель литературы. Напиши сочинение с кратким содержанием произведения '{text}' на русском языке, языком понятным школьнику."
    else:
        prompt = f"Представь что ты учитель литературы. Напиши сочинение на тему '{text}' на русском языке, языком понятным школьнику, минимум 1000 символов."

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
        await update.message.reply_text(
            f"Произошла ошибка при запросе к GigaChat: {str(e)}",
            reply_markup=SECTION_MENU
        )
    return ESSAY_RESULT

async def essay_result(update: Update, context):
    text = update.message.text.strip()
    text_no_emoji = emoji.replace_emoji(text, replace='').lower()
    text_no_emoji = re.sub(r'\s+', ' ', text_no_emoji).strip()
    logger.info(f"essay_result: Получен текст '{text}', без эмодзи: '{text_no_emoji}'")

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
        logger.warning(f"Недопустимый ввод в essay_result: '{text}'")
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
    user_id = update.effective_user.id
    if not can_make_request(user_id, context):
        remaining = get_remaining_requests(user_id, context)
        await update.message.reply_text(
            "Вы исчерпали лимит бесплатных запросов на сегодня (3 запроса в день). "
            "Для безлимитных запросов оформите подписку, выбрав 'Subscribe' в главном меню."
        )
        return
    logger.info("Пользователь выбрал раздел 'Математика'")
    await update.message.reply_text(
        "Напишите математическое уравнение, например: '2x + 3 = 7'",
        reply_markup=MATH_MENU
    )
    return EQUATION

def clean_latex_with_pandoc(text: str) -> str:
    try:
        cleaned_text = pypandoc.convert_text(text, 'plain', format='latex')
        cleaned_text = basic_latex_cleaning(cleaned_text)
        return cleaned_text.strip()
    except Exception as e:
        logger.error(f"Ошибка при преобразовании LaTeX через Pandoc: {e}")
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
        "\\div": "/",
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
    cleaned_text = re.sub(r'\\div\{([^}]+)\}', r'/(\1)', cleaned_text)
    cleaned_text = re.sub(r'([a-zA-Z])_\{([0-9]),([0-9])\}', lambda m: f"{m.group(1)}₁,₂", cleaned_text)
    cleaned_text = re.sub(r'([a-zA-Z])_([0-9])', lambda m: f"{m.group(1)}{chr(0x2080 + int(m.group(2)))}", cleaned_text)
    cleaned_text = re.sub(r'\\,', ' ', cleaned_text)
    cleaned_text = re.sub(r'/\s*\{([^}]+)\}\s*\{([^}]+)\}', r'\1/\2', cleaned_text)
    cleaned_text = re.sub(r'\\log', 'log', cleaned_text)
    cleaned_text = re.sub(r'\\([a-zA-Z]+)', r'\1', cleaned_text)
    return cleaned_text

def normalize_formatting(text: str) -> str:
    normalized_text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
    normalized_text = re.sub(r'\s+', ' ', normalized_text)
    normalized_text = re.sub(r'^(.*?)(\bШаг 1:)', r'\1\n\n\2', normalized_text, flags=re.MULTILINE)
    normalized_text = re.sub(r'(Шаг \d+:)(.*?)(?=Шаг \d+:|Итог:|$)', r'\1\2\n\n', normalized_text, flags=re.DOTALL)
    normalized_text = re.sub(r'(\S.*?)(Итог:)', r'\1\n\n\2', normalized_text, flags=re.DOTALL)
    normalized_text = re.sub(r'(\S.*?)(Ответ:)', r'\1\n\n\2', normalized_text, flags=re.DOTALL)
    normalized_text = re.sub(r'\n\s*\n+', '\n\n', normalized_text)
    normalized_text = normalized_text.rstrip('\n')
    return normalized_text

def highlight_equations(text: str) -> str:
    lines = text.split('\n')
    formatted_lines = []
    for line in lines:
        if '=' in line and any(c.isdigit() or c in 'xXyY' for c in line):
            formatted_lines.append(f"<b>{line.strip()}</b>")
        else:
            formatted_lines.append(line.strip())
    return '\n'.join(formatted_lines)

async def solve_equation(update: Update, context):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    text_no_emoji = emoji.replace_emoji(text, replace='').lower()
    text_no_emoji = re.sub(r'\s+', ' ', text_no_emoji).strip()
    logger.info(f"solve_equation: Получен текст '{text}', без эмодзи: '{text_no_emoji}'")

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

    # Увеличиваем счётчик запросов перед выполнением
    increment_request_count(user_id, context)
    remaining = get_remaining_requests(user_id, context)
    if remaining is not None:
        await update.message.reply_text(f"Осталось бесплатных запросов на сегодня: {remaining}")

    await update.message.reply_text(LOADING_MESSAGE)

    prompt = (
        f"Представь, что ты учитель математики, объясняющий задачу школьнику. "
        f"Реши уравнение или задачу '{text}' и подробно опиши процесс решения на русском языке простыми словами. "
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
        logger.error(f"Ошибка при запросе к GigaChat: {e}")
        await update.message.reply_text(
            "Произошла ошибка при обработке запроса. Попробуйте снова.",
            reply_markup=SECTION_MENU
        )
        return MATH_RESULT

    logger.debug(f"Исходный ответ от GigaChat: {response}")

    cleaned_response = clean_latex_with_pandoc(response)
    logger.debug(f"После очистки LaTeX: {cleaned_response}")

    normalized_response = normalize_formatting(cleaned_response)
    logger.debug(f"После нормализации форматирования: {normalized_response}")

    formatted_response = highlight_equations(normalized_response)
    logger.debug(f"После выделения уравнений: {formatted_response}")

    if len(formatted_response) > MAX_MESSAGE_LENGTH:
        formatted_response = formatted_response[:MAX_MESSAGE_LENGTH] + "..."
        logger.warning("Ответ обрезан из-за превышения лимита Telegram")

    try:
        await update.message.reply_text(
            FINAL_MESSAGE_TEMPLATE.format(formatted_response),
            reply_markup=SECTION_MENU,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения в Telegram: {e}")
        await update.message.reply_text(
            "Произошла ошибка при отправке ответа. Попробуйте снова.",
            reply_markup=SECTION_MENU
        )

    return MATH_RESULT

async def math_result(update: Update, context):
    text = update.message.text.strip()
    text_no_emoji = emoji.replace_emoji(text, replace='').lower()
    text_no_emoji = re.sub(r'\s+', ' ', text_no_emoji).strip()
    logger.info(f"math_result: Получен текст '{text}', без эмодзи: '{text_no_emoji}'")

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
        logger.warning(f"Недопустимый ввод в math_result: '{text}'")
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
    logger.warning(f"Неожиданный ввод текста: '{text}'")
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