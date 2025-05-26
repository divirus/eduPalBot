import aiohttp
import asyncio
import logging
from config import YANDEX_IAM_TOKEN, YANDEX_FOLDER_ID, YANDEX_API_URL, ACTIVE_AI_MODEL

logger = logging.getLogger(__name__)

async def query_yandexgpt(prompt, max_tokens=2048):
    if not YANDEX_IAM_TOKEN:
        logger.error("YANDEX_IAM_TOKEN не установлен. Проверьте .env файл.")
        raise ValueError("YANDEX_IAM_TOKEN не установлен. Убедитесь, что он добавлен в .env файл.")

    headers = {
        "Authorization": f"Bearer {YANDEX_IAM_TOKEN}",
        "x-folder-id": YANDEX_FOLDER_ID,
        "Content-Type": "application/json"
    }
    payload = {
        "modelUri": f"gpt://{YANDEX_FOLDER_ID}/yandexgpt-lite",
        "completionOptions": {"stream": False, "temperature": 0.1, "maxTokens": max_tokens},
        "messages": [
            {"role": "system", "text": "Ты - учитель-ассистент. Отвечай на русском языке простыми словами, избегай специальных символов и форматирования."},
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
    for attempt in range(max_retries):
        response = await query_yandexgpt(prompt, max_tokens)
        if "Ошибка" not in response:
            return response
        if attempt < max_retries - 1:
            await asyncio.sleep(delay)
            logger.info(f"Повтор попытки {attempt + 1} для Yandex GPT")
    return response

async def query_ai(prompt, max_tokens=2048):
    if ACTIVE_AI_MODEL == "yandexgpt":
        return await retry_query_yandexgpt(prompt, max_tokens)
    else:
        raise ValueError(f"Неизвестная модель AI: {ACTIVE_AI_MODEL}")