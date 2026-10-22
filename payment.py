from datetime import datetime, date, timedelta
from telegram import Update
from analytics import send_ga_event
import logging

logger = logging.getLogger(__name__)

# Daily free request limit
FREE_REQUESTS_LIMIT = 20

async def subscribe(update: Update, context):
    """
    Send a subscription payment request.
    
    Args:
        update (Update): Telegram update.
        context: Bot context.
    """
    await context.bot.sendPaymentRequest(
        chat_id=update.effective_chat.id,
        title="Месячная подписка",
        description="Безлимитные запросы на месяц",
        payload="subscription_monthly",
        currency="USD",
        amount=500  # 5 USD in cents
    )
    logger.info(f"Отправлен запрос на оплату для чата {update.effective_chat.id}")

async def pre_checkout_query(update: Update, context):
    """
    Approve a payment pre-checkout query.
    
    Args:
        update (Update): Telegram update.
        context: Bot context.
    """
    await update.pre_checkout_query.answer(True)
    logger.info(f"Подтверждён запрос на предпроверку для чата {update.effective_chat.id}")

async def successful_payment(update: Update, context):
    """
    Handle a successful payment and activate the subscription.
    
    Args:
        update (Update): Telegram update.
        context: Bot context.
    """
    user_id = update.effective_user.id
    from database import subscribe_user
    expiration_date = date.today() + timedelta(days=30)
    subscribe_user(user_id, expiration_date)
    if user_id not in context.user_data:
        context.user_data[user_id] = {}
    context.user_data[user_id].update({
        "subscribed": True,
        "expiration_date": expiration_date,
        "requests": {}  # Reset the request counter
    })
    await context.bot.send_message(
        chat_id=user_id,
        text="Ваша подписка активирована! Теперь у вас безлимитные запросы."
    )
    logger.info(f"Активирована подписка для пользователя {user_id}, срок до {expiration_date}")
    send_ga_event(user_id, "Subscription", "Activated", "Monthly Plan")

def is_subscribed(user_id, context):
    """
    Check whether the user has an active subscription.
    
    Args:
        user_id: User ID.
        context: Bot context.
    
    Returns:
        bool: True if the subscription is active, otherwise False.
    """
    user_data = context.user_data.get(user_id, {}).get("subscribed", False)
    expiration_date = context.user_data.get(user_id, {}).get("expiration_date", date.min)
    return user_data and expiration_date >= date.today()

def can_make_request(user_id, context):
    """
    Check whether the user can make a request.
    Return True if the subscription is active.
    Otherwise, check the free request limit.
    
    Args:
        user_id: User ID.
        context: Bot context.
    
    Returns:
        bool: True if the request is allowed, otherwise False.
    """
    if is_subscribed(user_id, context):
        return True

    # Check free requests
    user_data = context.user_data.get(user_id, {})
    requests = user_data.get("requests", {})
    today = str(date.today())  # Key for the current date

    # Reset the counter when the date changes
    if today not in requests:
        requests = {today: 0}
        user_data["requests"] = requests
        context.user_data[user_id] = user_data

    # Check the limit
    if requests[today] >= FREE_REQUESTS_LIMIT:
        return False
    return True

def increment_request_count(user_id, context):
    """
    Increment the user request counter.
    
    Args:
        user_id: User ID.
        context: Bot context.
    """
    if is_subscribed(user_id, context):
        return  # Do not count requests for subscribed users

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
    Return the number of remaining free requests.
    
    Args:
        user_id: User ID.
        context: Bot context.
    
    Returns:
        int: Number of remaining requests, or None if the subscription is active.
    """
    if is_subscribed(user_id, context):
        return None  # Unlimited requests for subscribed users
    user_data = context.user_data.get(user_id, {})
    requests = user_data.get("requests", {})
    today = str(date.today())
    used_requests = requests.get(today, 0)
    return max(0, FREE_REQUESTS_LIMIT - used_requests)