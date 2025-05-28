import aiohttp
import asyncio
import logging
from datetime import datetime, timedelta
from config import YANDEX_OAUTH_TOKEN, YANDEX_FOLDER_ID, YANDEX_API_URL, YANDEX_IAM_URL, ACTIVE_AI_MODEL

logger = logging.getLogger(__name__)

# Глобальные переменные для хранения IAM-токена и времени его истечения
iam_token = None
token_expiry = None

async def refresh_iam_token():
    """Обновляет IAM-токен с использованием OAuth-токена."""
    if not YANDEX_OAUTH_TOKEN:
        logger.error("YANDEX_OAUTH_TOKEN не установлен. Проверьте .env файл.")
        raise ValueError("YANDEX_OAUTH_TOKEN не установлен. Убедитесь, что он добавлен в .env файл.")

    headers = {"Content-Type": "application/json"}
    payload = {"yandexPassportOauthToken": YANDEX_OAUTH_TOKEN}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(YANDEX_IAM_URL, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    data = await response.json()
                    new_iam_token = data["iamToken"]
                    # Предполагаем, что токен действителен 12 часов
                    new_token_expiry = datetime.now() + timedelta(hours=12)
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
    """Возвращает действующий IAM-токен, обновляя его при необходимости."""
    global iam_token, token_expiry
    if iam_token is None or datetime.now() >= token_expiry:
        iam_token, token_expiry = await refresh_iam_token()
    return iam_token

async def query_yandexgpt(prompt, max_tokens=2048):
    """Выполняет запрос к Yandex GPT с использованием действующего IAM-токена."""
    iam_token = await get_valid_iam_token()
    headers = {
        "Authorization": f"Bearer {iam_token}",
        "x-folder-id": YANDEX_FOLDER_ID,
        "Content-Type": "application/json"
    }
    payload = {
        "modelUri": f"gpt://{YANDEX_FOLDER_ID}/yandexgpt-lite",
        "completionOptions": {"stream": False, "temperature": 0.1, "maxTokens": max_tokens},
        "messages": [
            {"role": "system", "text": "Ты - учитель. Отвечай на русском языке простыми словами, понятными школьнику, избегай специальных символов и форматирования."},
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