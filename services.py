import aiohttp
import logging
import asyncio
import ssl
import uuid
import re
from config import GIGACHAT_AUTH_KEY, GIGACHAT_API_URL, GIGACHAT_OAUTH_URL, CERT_PATH
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

access_token = None
token_expiry = None

async def get_access_token():
    """Получает токен доступа через OAuth 2.0"""
    global access_token, token_expiry

    if access_token and token_expiry and datetime.now() < token_expiry:
        return access_token

    ssl_context = ssl.create_default_context(cafile=CERT_PATH)

    headers = {
        "Authorization": f"Basic {GIGACHAT_AUTH_KEY}",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "RqUID": str(uuid.uuid4())
    }
    data = {
        "grant_type": "client_credentials",
        "scope": "GIGACHAT_API_PERS",
        "model": "GigaChat-Pro"
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                GIGACHAT_OAUTH_URL,
                headers=headers,
                data=data,
                ssl=ssl_context,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                response_text = await response.text()
                logger.info(f"Статус ответа OAuth: {response.status}")
                logger.info(f"Тело ответа OAuth: {response_text}")
                response.raise_for_status()
                token_data = await response.json()
                access_token = token_data["access_token"]
                expires_at_ms = token_data["expires_at"]
                expires_at_seconds = expires_at_ms / 1000
                token_expiry = datetime.fromtimestamp(expires_at_seconds) - timedelta(seconds=60)
                logger.info("Токен успешно получен")
                return access_token
        except aiohttp.ClientError as e:
            logger.error(f"Ошибка при получении токена: {str(e)}")
            raise
        except KeyError as e:
            logger.error(f"Отсутствует ожидаемый ключ в ответе OAuth: {str(e)}")
            raise

async def query_gigachat(prompt, max_tokens=2048):
    """Асинхронный запрос к GigaChat API"""
    global access_token, token_expiry

    if not access_token or datetime.now() >= token_expiry:
        await get_access_token()

    ssl_context = ssl.create_default_context(cafile=CERT_PATH)

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "GigaChat",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                GIGACHAT_API_URL,
                headers=headers,
                json=payload,
                ssl=ssl_context,
                timeout=aiohttp.ClientTimeout(total=600)
            ) as response:
                logger.info(f"Status code API: {response.status}")
                raw_text = await response.text()
                logger.info(f"Raw response API: {raw_text}")

                if response.status == 200:
                    json_response = await response.json()
                    if "choices" in json_response and len(json_response["choices"]) > 0:
                        text = json_response["choices"][0]["message"]["content"].strip()
                        if not text:
                            logger.warning("Ответ API пустой")
                            return "Ответ пустой\. Попробуем ещё\?"
                        formatted_text = text
                        logger.info(f"Processed response API: {formatted_text}")
                        return formatted_text
                    else:
                        logger.error("Неверный формат ответа API")
                        return "Ошибка: Неверный формат ответа от API"
                else:
                    logger.error(f"Запрос провалился с кодом: {response.status}")
                    return f"Не смог сгенерировать ответ\. Код ошибки: {response.status}"
        except asyncio.TimeoutError:
            logger.error("Время ожидания истекло (10 минут)")
            return "Время ожидания истекло \(10 минут $$\. Попробуйте снова\."
        except aiohttp.ClientError as e:
            logger.error(f"Ошибка при запросе: {str(e)}")
            return f"Ошибка при запросе: {str(e)}"

async def retry_query_gigachat(prompt, max_tokens=2048, max_retries=3, delay=5):
    """Асинхронный повтор запроса при ошибке"""
    for attempt in range(max_retries):
        response = await query_gigachat(prompt, max_tokens)
        escaped_response = response  # Экранируем текст
        if "Ошибка" not in escaped_response and "Время ожидания" not in escaped_response:
            return escaped_response
        if attempt < max_retries - 1:
            await asyncio.sleep(delay)
            logger.info(f"Повтор попытки {attempt + 1} после задержки {delay} секунд")
            continue
        return escaped_response