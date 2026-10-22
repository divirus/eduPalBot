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
#     Send an event to Graspil asynchronously with enriched properties.
    
#     Args:
#         user_id: Telegram user ID.
#         event_name: Event name (for example, "bot_start").
#         context: Bot context providing access to user_data.
#         bot_platform: Bot platform (defaults to "Telegram").
#         max_retries: Maximum number of delivery attempts.
#         retry_delay: Delay between attempts in seconds.
#         **properties: Additional event properties.
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
#                         logger.info(f"Event '{event_name}' sent (user_id={user_id})")
#                         return True
                    
#                     error_text = await response.text()
#                     logger.warning(
#                         f"Attempt {attempt + 1}: Graspil returned {response.status}. "
#                         f"Error: {error_text[:200]}..."  # Truncate long text
#                     )
                    
#             except (aiohttp.ClientError, asyncio.TimeoutError) as e:
#                 logger.warning(
#                     f"Attempt {attempt + 1}: Graspil connection error: {str(e)}"
#                 )

#             if attempt < max_retries - 1:
#                 await asyncio.sleep(retry_delay)

#         logger.error(f"Event '{event_name}' was not sent after {max_retries} attempts")
#         return False

def send_ga_event(user_id, event_category, event_action, event_label=None, event_value=None):
    """
    Send an event to Google Analytics using the Measurement Protocol.
    :param user_id: Telegram user ID
    :param event_category: Event category (for example, "Subscription")
    :param event_action: Event action (for example, "Activated")
    :param event_label: Optional label (for example, "Monthly Plan")
    :param event_value: Optional value (for example, the request count)
    """
    data = {
        "v": "1",              # Protocol version
        "tid": GOOGLE_ANALYTICS_ID, # Tracking ID
        "cid": str(user_id),   # Client ID (uses the Telegram user_id)
        "t": "event",          # Hit type: event
        "ec": event_category,  # Event category
        "ea": event_action,    # Action
        "el": event_label,     # Label (optional)
        "ev": event_value      # Value (optional)
    }

    # Remove None values from the dictionary
    payload = {k: v for k, v in data.items() if v is not None}

    try:
        response = requests.post("https://www.google-analytics.com/collect", data=payload)
        if response.status_code == 200:
            print(f"Событие отправлено в GA: {event_category} - {event_action}")
        else:
            print(f"Ошибка отправки в GA: {response.status_code}")
    except Exception as e:
        print(f"Исключение при отправке в GA: {e}")

# Example call
if __name__ == "__main__":
    send_ga_event(12345, "Subscription", "Activated", "Monthly Plan")