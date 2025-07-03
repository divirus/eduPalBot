from datetime import datetime, date
from telegram import Update, Bot
from analytics import send_ga_event
from datetime import date, timedelta
import logging

logger = logging.getLogger(__name__)

# Константа для лимита бесплатных запросов в день
FREE_REQUESTS_LIMIT = 20

async def successful_payment(update: Update, context):
    user_id = update.effective_user.id
    from database import set_subscribed
    expiration_date = date.today() + timedelta(days=30)
    set_subscribed(user_id, expiration_date)
    await context.bot.send_message(chat_id=user_id, text="Ваша подписка активирована!")
    
    # Отправка события в Google Analytics
    send_ga_event(user_id, "Subscription", "Activated", "Monthly Plan")

async def subscribe(update: Update, context):
    """
    Отправляет запрос на оплату подписки.
    
    Args:
        update (Update): Обновление от Telegram.
        context: Контекст бота.
    """
    await context.bot.sendPaymentRequest(
        chat_id=update.effective_chat.id,
        title="Месячная подписка",
        description="Безлимитные запросы на месяц",
        payload="subscription_monthly",
        currency="USD",
        amount=500  # 5 USD в центах
    )
    logger.info(f"Отправлен запрос на оплату для чата {update.effective_chat.id}")

async def pre_checkout_query(update: Update, context):
    """
    Подтверждает запрос на предпроверку оплаты.
    
    Args:
        update (Update): Обновление от Telegram.
        context: Контекст бота.
    """
    await update.pre_checkout_query.answer(True)
    logger.info(f"Подтверждён запрос на предпроверку для чата {update.effective_chat.id}")

async def successful_payment(update: Update, context):
    """
    Обрабатывает успешную оплату и активирует подписку.
    
    Args:
        update (Update): Обновление от Telegram.
        context: Контекст бота.
    """
    user_id = update.effective_user.id
    expiration_date = date.today() + datetime.timedelta(days=30)
    context.user_data[user_id] = {
        "subscribed": True,
        "expiration_date": expiration_date,
        "requests": {}  # Сбрасываем счётчик запросов при подписке
    }
    await context.bot.send_message(chat_id=user_id, text="Ваша подписка активирована! Теперь у вас безлимитные запросы.")
    logger.info(f"Активирована подписка для пользователя {user_id}, срок до {expiration_date}")

def is_subscribed(user_id, context):
    """
    Проверяет, активна ли подписка у пользователя.
    
    Args:
        user_id: ID пользователя.
        context: Контекст бота.
    
    Returns:
        bool: True, если подписка активна, иначе False.
    """
    user_data = context.user_data.get(user_id, {}).get("subscribed", False)
    expiration_date = context.user_data.get(user_id, {}).get("expiration_date", date.min)
    return user_data and expiration_date >= date.today()

def can_make_request(user_id, context):
    """
    Проверяет, может ли пользователь сделать запрос.
    Если подписка активна, возвращает True.
    Если нет подписки, проверяет лимит бесплатных запросов.
    
    Args:
        user_id: ID пользователя.
        context: Контекст бота.
    
    Returns:
        bool: True, если запрос разрешён, иначе False.
    """
    if is_subscribed(user_id, context):
        return True

    # Проверяем бесплатные запросы
    user_data = context.user_data.get(user_id, {})
    requests = user_data.get("requests", {})
    today = str(date.today())  # Ключ для текущей даты

    # Если дата изменилась, сбрасываем счётчик
    if today not in requests:
        requests = {today: 0}
        user_data["requests"] = requests
        context.user_data[user_id] = user_data

    # Проверяем лимит
    if requests[today] >= FREE_REQUESTS_LIMIT:
        return False
    return True

def increment_request_count(user_id, context):
    """
    Увеличивает счётчик запросов пользователя.
    
    Args:
        user_id: ID пользователя.
        context: Контекст бота.
    """
    if is_subscribed(user_id, context):
        return  # Подписанным пользователям не считаем запросы

    user_data = context.user_data.get(user_id, {})
    requests = user_data.get("requests", {})
    today = str(date.today())

    if today not in requests:
        requests[today] = 0
    requests[today] += 1
    user_data["requests"] = requests
    context.user_data[user_id] = user_data
    logger.info(f"Пользователь {user_id} сделал запрос. Осталось бесплатных запросов: {FREE_REQUESTS_LIMIT - requests[today]}")

def get_remaining_requests(user_id, context):
    """
    Возвращает количество оставшихся бесплатных запросов.
    
    Args:
        user_id: ID пользователя.
        context: Контекст бота.
    
    Returns:
        int: Количество оставшихся запросов или None, если подписка активна.
    """
    if is_subscribed(user_id, context):
        return None  # Безлимит для подписанных пользователей
    user_data = context.user_data.get(user_id, {})
    requests = user_data.get("requests", {})
    today = str(date.today())
    used_requests = requests.get(today, 0)
    return max(0, FREE_REQUESTS_LIMIT - used_requests)