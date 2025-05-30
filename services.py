import aiohttp
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from config import YANDEX_OAUTH_TOKEN, YANDEX_FOLDER_ID, YANDEX_API_URL, YANDEX_IAM_URL, ACTIVE_AI_MODEL

logger = logging.getLogger(__name__)

# Глобальные переменные для хранения IAM-токена и времени его истечения
iam_token = None
token_expiry = None
token_lock = asyncio.Lock()  # Блокировка для безопасного обновления токена

async def refresh_iam_token():
    """Обновляет IAM-токен с использованием OAuth-токена."""
    global iam_token, token_expiry
    
    if not YANDEX_OAUTH_TOKEN:
        logger.error("YANDEX_OAUTH_TOKEN не установлен. Проверьте .env файл.")
        raise ValueError("YANDEX_OAUTH_TOKEN не установлен. Убедитесь, что он добавлен в .env файл.")

    headers = {"Content-Type": "application/json"}
    payload = {"yandexPassportOauthToken": YANDEX_OAUTH_TOKEN}
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                YANDEX_IAM_URL, 
                headers=headers, 
                json=payload, 
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    new_iam_token = data["iamToken"]
                    expires_at_str = data["expiresAt"]
                    
                    # Логируем строку времени для диагностики
                    logger.debug(f"Получено время истечения: {expires_at_str}")
                    
                    # Парсим время истечения с учетом часового пояса
                    try:
                        # Формат с миллисекундами: 2023-10-19T07:20:30.345Z
                        expires_at = datetime.strptime(
                            expires_at_str, 
                            "%Y-%m-%dT%H:%M:%S.%fZ"
                        ).replace(tzinfo=timezone.utc)
                    except ValueError:
                        try:
                            # Формат с наносекундами: 2025-05-29T06:51:08.603015186Z
                            # Обрезаем до микросекунд (6 цифр)
                            if '.' in expires_at_str:
                                base_time, fraction = expires_at_str.split('.')
                                fraction = fraction[:6] + 'Z'  # Оставляем только 6 цифр
                                expires_at_str = f"{base_time}.{fraction}"
                            expires_at = datetime.strptime(
                                expires_at_str, 
                                "%Y-%m-%dT%H:%M:%S.%fZ"
                            ).replace(tzinfo=timezone.utc)
                        except ValueError:
                            # Формат без миллисекунд: 2023-10-19T07:20:30Z
                            expires_at = datetime.strptime(
                                expires_at_str, 
                                "%Y-%m-%dT%H:%M:%SZ"
                            ).replace(tzinfo=timezone.utc)
                    
                    # Преобразуем в наивный datetime (без часового пояса)
                    new_token_expiry = expires_at.replace(tzinfo=None)
                    
                    logger.info("IAM-токен успешно обновлён")
                    return new_iam_token, new_token_expiry
                else:
                    error_text = await response.text()
                    logger.error(f"Ошибка при получении IAM-токена: {response.status} - {error_text}")
                    raise Exception(f"Не удалось получить IAM-токен: {error_text}")
        except Exception as e:
            logger.error(f"Ошибка при запросе IAM-токена: {str(e)}")
            raise

async def get_valid_iam_token():
    """Возвращает действующий IAM-токен, обновляем его при необходимости."""
    global iam_token, token_expiry
    
    # Текущее время в UTC
    now = datetime.utcnow()
    
    # Если токен существует и еще действителен (с запасом 5 минут)
    if iam_token and token_expiry and now < token_expiry - timedelta(minutes=5):
        return iam_token
    
    # Если токен требует обновления
    async with token_lock:
        # Повторная проверка после получения блокировки
        if iam_token and token_expiry and now < token_expiry - timedelta(minutes=5):
            return iam_token
        
        try:
            iam_token, token_expiry = await refresh_iam_token()
            logger.info(f"Обновлён IAM-токен, действителен до: {token_expiry}")
            return iam_token
        except Exception as e:
            logger.error(f"Критическая ошибка при обновлении IAM-токена: {str(e)}")
            if iam_token and token_expiry and now < token_expiry:
                logger.warning("Используется старый IAM-токен, так как обновление не удалось")
                return iam_token
            raise

async def query_yandexgpt(prompt, max_tokens=2048):
    """Выполняет запрос к Yandex GPT с использованием действующего IAM-токена."""
    iam_token = await get_valid_iam_token()
    headers = {
        "Authorization": f"Bearer {iam_token}",
        "x-folder-id": YANDEX_FOLDER_ID,
        "Content-Type": "application/json"
    }
    payload = {
        "modelUri": f"gpt://{YANDEX_FOLDER_ID}/yandexgpt-pro",
        "completionOptions": {"stream": False, "temperature": 0.1, "maxTokens": max_tokens},
        "messages": [
            {"role": "system", "text": "Ты - учитель. Ты отлично разбираешься в русском языке, литературе и математике. Отвечай на русском языке простыми словами, понятными школьнику, избегай специальных символов и форматирования."},
            {"role": "user", "text": prompt}
        ]
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(YANDEX_API_URL, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=600)) as response:
                if response.status == 200:
                    data = await response.json()
                    return data["result"]["alternatives"][0]["message"]["text"].strip()
                else:
                    error_text = await response.text()
                    logger.error(f"Yandex GPT ошибка: {response.status} - {error_text}")
                    return f"Ошибка Yandex GPT: {response.status} - {error_text}"
        except Exception as e:
            logger.error(f"Ошибка при запросе к Yandex GPT: {str(e)}")
            return f"Ошибка соединения: {str(e)}"

async def retry_query_yandexgpt(prompt, max_tokens=2048, max_retries=3, delay=5):
    """Повторяет запрос к Yandex GPT в случае ошибки."""
    for attempt in range(max_retries):
        response = await query_yandexgpt(prompt, max_tokens)
        if "Ошибка" not in response:
            return response
        if attempt < max_retries - 1:
            await asyncio.sleep(delay)
            logger.info(f"Повтор попытки {attempt + 1} для Yandex GPT")
    return response

async def query_ai(prompt, max_tokens=2048):
    """Обрабатывает запрос к активной модели AI."""
    if ACTIVE_AI_MODEL == "yandexgpt":
        return await retry_query_yandexgpt(prompt, max_tokens)
    else:
        raise ValueError(f"Неизвестная модель AI: {ACTIVE_AI_MODEL}")