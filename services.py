import aiohttp
import logging
import asyncio
from datetime import datetime, timedelta
from config import (
    YANDEX_OAUTH_TOKEN, YANDEX_FOLDER_ID, YANDEX_API_URL, YANDEX_IAM_URL,
    ACTIVE_AI_MODEL
)

logger = logging.getLogger(__name__)

# YandexGPT Auth
yandex_iam_token = None
yandex_token_expiry = None

async def get_yandex_iam_token():
    global yandex_iam_token, yandex_token_expiry
    if yandex_iam_token and datetime.now() < yandex_token_expiry:
        return yandex_iam_token

    headers = {"Content-Type": "application/json"}
    payload = {"jwt": YANDEX_OAUTH_TOKEN}
    
    async with aiohttp.ClientSession() as session:
        async with session.post(YANDEX_IAM_URL, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as response:
            response.raise_for_status()
            token_data = await response.json()
            yandex_iam_token = token_data["iamToken"]
            yandex_token_expiry = datetime.now() + timedelta(hours=1)
            logger.info("Токен Yandex GPT успешно получен")
            return yandex_iam_token

async def query_yandexgpt(prompt, max_tokens=2048):
    global yandex_iam_token
    if not yandex_iam_token:
        await get_yandex_iam_token()

    headers = {
        "Authorization": f"Bearer {yandex_iam_token}",
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
        async with session.post(YANDEX_API_URL, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=600)) as response:
            if response.status == 200:
                data = await response.json()
                return data["result"]["alternatives"][0]["message"]["text"].strip()
            logger.error(f"Yandex GPT ошибка: {response.status}")
            return f"Ошибка Yandex GPT: {response.status}"

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