import os
import aiohttp
import asyncio
import logging
from datetime import datetime
from config import GRASPIL_API_KEY, GRASPIL_API_URL
# from payment import is_subscribed, get_remaining_requests
# from payment import FREE_REQUESTS_LIMIT
import requests

GOOGLE_ANALYTICS_ID = os.getenv("GOOGLE_ANALYTICS_ID")

logger = logging.getLogger(__name__)

# async def send_event_to_graspil(
#     user_id: int,
#     event_name: str,
#     context,
#     bot_platform: str = "Telegram",
#     max_retries: int = FREE_REQUESTS_LIMIT,
#     retry_delay: float = 1.0,
#     **properties
# ):
#     """
#     Асинхронно отправляет событие в Graspil с обогащенными данными.
    
#     Args:
#         user_id: ID пользователя в Telegram.
#         event_name: Название события (например, "bot_start").
#         context: Контекст бота (для доступа к user_data).
#         bot_platform: Платформа бота (по умолчанию "Telegram").
#         max_retries: Максимальное количество попыток отправки.
#         retry_delay: Задержка между попытками в секундах.
#         **properties: Дополнительные свойства события.
#     """
#     payload = {
#         "user_id": str(user_id),
#         "event": event_name,
#         "timestamp": datetime.utcnow().isoformat() + "Z",
#         "platform": bot_platform,
#         "properties": {
#             **properties,
#             "is_subscribed": is_subscribed(user_id, context),
#             "remaining_requests": get_remaining_requests(user_id, context)
#         }
#     }

#     headers = {
#         "Authorization": f"Bearer {GRASPIL_API_KEY}",
#         "Content-Type": "application/json"
#     }

#     async with aiohttp.ClientSession() as session:
#         for attempt in range(max_retries):
#             try:
#                 async with session.post(
#                     GRASPIL_API_URL,
#                     headers=headers,
#                     json=payload,
#                     timeout=aiohttp.ClientTimeout(total=5)
#                 ) as response:
                    
#                     if response.status == 200:
#                         logger.info(f"Событие '{event_name}' отправлено (user_id={user_id})")
#                         return True
                    
#                     error_text = await response.text()
#                     logger.warning(
#                         f"Попытка {attempt + 1}: Graspil вернул {response.status}. "
#                         f"Ошибка: {error_text[:200]}..."  # Обрезаем длинный текст
#                     )
                    
#             except (aiohttp.ClientError, asyncio.TimeoutError) as e:
#                 logger.warning(
#                     f"Попытка {attempt + 1}: Ошибка подключения к Graspil: {str(e)}"
#                 )

#             if attempt < max_retries - 1:
#                 await asyncio.sleep(retry_delay)

#         logger.error(f"Событие '{event_name}' не отправлено после {max_retries} попыток")
#         return False

def send_ga_event(user_id, event_category, event_action, event_label=None, event_value=None):
    """
    Отправляет событие в Google Analytics через Measurement Protocol.
    :param user_id: ID пользователя Telegram
    :param event_category: Категория события (например, "Subscription")
    :param event_action: Действие (например, "Activated")
    :param event_label: Метка (опционально, например, "Monthly Plan")
    :param event_value: Значение (опционально, например, количество запросов)
    """
    data = {
        "v": "1",              # Версия протокола
        "tid": GOOGLE_ANALYTICS_ID, # Tracking ID
        "cid": str(user_id),   # Client ID (используем user_id Telegram)
        "t": "event",          # Тип хита: событие
        "ec": event_category,  # Категория события
        "ea": event_action,    # Действие
        "el": event_label,     # Метка (опционально)
        "ev": event_value      # Значение (опционально)
    }

    # Убираем None из словаря
    payload = {k: v for k, v in data.items() if v is not None}

    try:
        response = requests.post("https://www.google-analytics.com/collect", data=payload)
        if response.status_code == 200:
            print(f"Событие отправлено в GA: {event_category} - {event_action}")
        else:
            print(f"Ошибка отправки в GA: {response.status_code}")
    except Exception as e:
        print(f"Исключение при отправке в GA: {e}")

# Пример вызова
if __name__ == "__main__":
    send_ga_event(12345, "Subscription", "Activated", "Monthly Plan")