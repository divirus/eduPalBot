import aiohttp
import logging
from datetime import datetime
from config import GRASPIL_API_KEY, GRASPIL_API_URL
from payment import is_subscribed, get_remaining_requests

logger = logging.getLogger(__name__)

async def send_event_to_graspil(
    user_id: int,
    event_name: str,
    context,
    bot_platform: str = "Telegram",
    max_retries: int = 3,
    **properties
):
    """
    Отправляет событие в Graspil с автоматическим добавлением данных о подписке и лимитах.
    
    :param user_id: ID пользователя в Telegram.
    :param event_name: Название события (например, "bot_start").
    :param context: Контекст бота (для проверки подписки и лимитов).
    :param bot_platform: Платформа бота (по умолчанию "Telegram").
    :param max_retries: Количество попыток отправки при ошибках.
    :param properties: Дополнительные свойства события.
    """
    # Добавляем стандартные свойства
    payload = {
        "user_id": str(user_id),
        "event": event_name,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "platform": bot_platform,
        "properties": {
            **properties,
            "is_subscribed": is_subscribed(user_id, context),
            "remaining_requests": get_remaining_requests(user_id, context)
        }
    }

    headers = {
        "Authorization": f"Bearer {GRASPIL_API_KEY}",
        "Content-Type": "application/json"
    }

    async with aiohttp.ClientSession() as session:
        for attempt in range(max_retries):
            try:
                async with session.post(
                    GRASPIL_API_URL,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    
                    if response.status == 200:
                        logger.info(f"Событие '{event_name}' отправлено для user_id={user_id}")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Ошибка {response.status}: {error_text}")
                        if attempt == max_retries - 1:
                            return False

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.error(f"Попытка {attempt + 1}/{max_retries} не удалась: {str(e)}")
                if attempt == max_retries - 1:
                    return False
                await asyncio.sleep(1)  # Задержка между попытками

        return False