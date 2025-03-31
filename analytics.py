import aiohttp
import asyncio
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
    retry_delay: float = 1.0,
    **properties
):
    """
    Асинхронно отправляет событие в Graspil с обогащенными данными.
    
    Args:
        user_id: ID пользователя в Telegram.
        event_name: Название события (например, "bot_start").
        context: Контекст бота (для доступа к user_data).
        bot_platform: Платформа бота (по умолчанию "Telegram").
        max_retries: Максимальное количество попыток отправки.
        retry_delay: Задержка между попытками в секундах.
        **properties: Дополнительные свойства события.
    """
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
                        logger.info(f"Событие '{event_name}' отправлено (user_id={user_id})")
                        return True
                    
                    error_text = await response.text()
                    logger.warning(
                        f"Попытка {attempt + 1}: Graspil вернул {response.status}. "
                        f"Ошибка: {error_text[:200]}..."  # Обрезаем длинный текст
                    )
                    
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.warning(
                    f"Попытка {attempt + 1}: Ошибка подключения к Graspil: {str(e)}"
                )

            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)

        logger.error(f"Событие '{event_name}' не отправлено после {max_retries} попыток")
        return False