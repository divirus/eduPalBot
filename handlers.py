import logging
from telegram import Update
from telegram.ext import CommandHandler, MessageHandler, ConversationHandler, filters
from keyboards import MAIN_MENU, SECTION_MENU, SUBSECTION_MENU, ESSAY_TYPE_MENU, MATH_MENU
from gigachat.services import retry_query_gigachat

# Состояния для ConversationHandler
ESSAY_TYPE, WAITING_FOR_THEME, ESSAY_RESULT, EQUATION, MATH_RESULT, LOGIC_INPUT, LOGIC_RESULT = range(7)
logger = logging.getLogger(__name__)


async def _generate_or_notify_failure(update, prompt, max_tokens, reply_markup):
    try:
        return await retry_query_gigachat(prompt, max_tokens=max_tokens)
    except Exception as error:
        logger.error("Ошибка при запросе к GigaChat (%s)", type(error).__name__)
        await update.message.reply_text(
            "Не удалось получить ответ. Попробуйте ещё раз позже.",
            reply_markup=reply_markup,
        )
        return None

async def start(update: Update, context):
    user = update.message.from_user.first_name
    welcome_message = (
        f"Привет, {user}! Я бот-помощник для школьников 1-7 классов и их родителей.\n"
        "Выберите раздел ниже:"
    )
    await update.message.reply_text(welcome_message, reply_markup=MAIN_MENU)
    return ConversationHandler.END

async def essay(update: Update, context):
    await update.message.reply_text(
        "Выберите тип сочинения:",
        reply_markup=ESSAY_TYPE_MENU,
        parse_mode='MarkdownV2'
    )
    return ESSAY_TYPE

async def essay_type(update: Update, context):
    text = update.message.text.lower()
    if text == "назад":
        await update.message.reply_text(
            "Возвращаемся в главное меню\!",
            reply_markup=MAIN_MENU,
            parse_mode='MarkdownV2'
        )
        return ConversationHandler.END

    context.user_data['essay_type'] = text

    if text == "краткое содержание произведения":
        await update.message.reply_text(
            "Пожалуйста, введите название произведения:",
            reply_markup=SUBSECTION_MENU,
            parse_mode='MarkdownV2'
        )
    elif text == "сочинение по теме":
        await update.message.reply_text(
            "Пожалуйста, введите тему сочинения:",
            reply_markup=SUBSECTION_MENU,
            parse_mode='MarkdownV2'
        )
    else:
        await update.message.reply_text(
            "Выберите *Краткое содержание произведения* или *Сочинение по теме*:",
            reply_markup=ESSAY_TYPE_MENU,
            parse_mode='MarkdownV2'
        )
        return ESSAY_TYPE

    return WAITING_FOR_THEME

async def waiting_for_theme(update: Update, context):
    text = update.message.text.lower()

    if text == "в главное меню":
        await update.message.reply_text(
            "Возвращаемся в главное меню\!",
            reply_markup=MAIN_MENU,
            parse_mode='MarkdownV2'
        )
        return ConversationHandler.END
    elif text == "назад":
        await update.message.reply_text(
            "Выберите тип сочинения:",
            reply_markup=ESSAY_TYPE_MENU,
            parse_mode='MarkdownV2'
        )
        return ESSAY_TYPE

    context.user_data['essay_theme'] = text

    if context.user_data['essay_type'] == "краткое содержание произведения":
        prompt = f"Напиши краткое содержание произведения '{text}' на русском языке, понятное школьнику."
    else:
        prompt = f"Напиши сочинение на тему '{text}' на русском языке, понятное школьнику."

    await update.message.reply_text(
        "Пожалуйста, дождитесь ответа\.\.\.",
        parse_mode='MarkdownV2'
    )
    response = await _generate_or_notify_failure(update, prompt, 2048, SECTION_MENU)
    if response is None:
        return ESSAY_RESULT
    if len(response) > 4000:
        response = response[:4000] + "..."
    await update.message.reply_text(
        f"Сочинение:\n{response}",
        reply_markup=SECTION_MENU
    )
    return ESSAY_RESULT

async def essay_result(update: Update, context):
    text = update.message.text.lower()
    if text == "новый запрос":
        await essay(update, context)
        return ESSAY_TYPE
    elif text == "в главное меню":
        await update.message.reply_text(
            "Возвращаемся в главное меню\!",
            reply_markup=MAIN_MENU,
            parse_mode='MarkdownV2'
        )
        return ConversationHandler.END
    return ESSAY_RESULT

async def math(update: Update, context):
    await update.message.reply_text(
        "Напиши уравнение, например: '2x + 3 = 7'\.",
        reply_markup=MATH_MENU,
        parse_mode='MarkdownV2'
    )
    return EQUATION

async def solve_equation(update: Update, context):
    text = update.message.text.lower()
    if text == "в главное меню":
        await update.message.reply_text(
            "Возвращаемся в главное меню\!",
            reply_markup=MAIN_MENU,
            parse_mode='MarkdownV2'
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "Пожалуйста, дождитесь ответа\.\.\.",
        parse_mode='MarkdownV2'
    )
    prompt = f"Реши уравнение '{text}' пошагово на русском языке. Используй простой язык для школьника."
    response = await _generate_or_notify_failure(update, prompt, 512, SECTION_MENU)
    if response is None:
        return MATH_RESULT
    if len(response) > 4000:
        response = response[:4000] + "..."
    await update.message.reply_text(
        f"Объяснение:\n{response}\nЕсли непонятно, уточни!",
        reply_markup=SECTION_MENU
    )
    return MATH_RESULT

async def math_result(update: Update, context):
    text = update.message.text.lower()
    if text == "новый запрос":
        await math(update, context)
        return EQUATION
    elif text == "в главное меню":
        await update.message.reply_text(
            "Возвращаемся в главное меню\!",
            reply_markup=MAIN_MENU,
            parse_mode='MarkdownV2'
        )
        return ConversationHandler.END
    return MATH_RESULT

async def logic(update: Update, context):
    await update.message.reply_text(
        "Введите текст логической задачи, которую нужно решить:",
        reply_markup=SUBSECTION_MENU,
        parse_mode='MarkdownV2'
    )
    return LOGIC_INPUT

async def logic_input(update: Update, context):
    text = update.message.text.lower()
    if text == "в главное меню":
        await update.message.reply_text(
            "Возвращаемся в главное меню\!",
            reply_markup=MAIN_MENU,
            parse_mode='MarkdownV2'
        )
        return ConversationHandler.END
    elif text == "назад":
        await update.message.reply_text(
            "Введите текст логической задачи, которую нужно решить:",
            reply_markup=SUBSECTION_MENU,
            parse_mode='MarkdownV2'
        )
        return LOGIC_INPUT

    context.user_data['logic_task'] = text
    await update.message.reply_text(
        "Пожалуйста, дождитесь ответа\.\.\.",
        parse_mode='MarkdownV2'
    )
    prompt = f"Реши логическую задачу: '{text}'. Дай решение с объяснением на русском языке, понятное школьнику."
    response = await _generate_or_notify_failure(update, prompt, 512, SECTION_MENU)
    if response is None:
        return LOGIC_RESULT
    if len(response) > 4000:
        response = response[:4000] + "..."
    await update.message.reply_text(
        f"Решение:\n{response}",
        reply_markup=SECTION_MENU
    )
    return LOGIC_RESULT

async def logic_result(update: Update, context):
    text = update.message.text.lower()
    if text == "новый запрос":
        await logic(update, context)
        return LOGIC_INPUT
    elif text == "в главное меню":
        await update.message.reply_text(
            "Возвращаемся в главное меню\!",
            reply_markup=MAIN_MENU,
            parse_mode='MarkdownV2'
        )
        return ConversationHandler.END
    return LOGIC_RESULT

async def handle_question(update: Update, context):
    text = update.message.text
    if text == "Сочинения":
        await essay(update, context)
        return ESSAY_TYPE
    elif text == "Математика":
        await math(update, context)
        return EQUATION
    elif text == "Логика":
        await logic(update, context)
        return LOGIC_INPUT
    else:
        await update.message.reply_text(
            "Пожалуйста, дождитесь ответа\.\.\.",
            parse_mode='MarkdownV2'
        )
        prompt = f"Объясни на русском языке для школьника: {text}"
        response = await _generate_or_notify_failure(update, prompt, 512, MAIN_MENU)
        if response is None:
            return
        if len(response) > 4000:
            response = response[:4000] + "..."
        await update.message.reply_text(
            f"Ответ:\n{response}",
            reply_markup=MAIN_MENU
        )

async def cancel(update: Update, context):
    await update.message.reply_text(
        "Если что — пиши снова\!",
        reply_markup=MAIN_MENU,
        parse_mode='MarkdownV2'
    )
    return ConversationHandler.END
