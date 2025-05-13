import aiohttp
import logging
import asyncio
import ssl
import uuid
from datetime import datetime, timedelta
from config import (
    GIGACHAT_AUTH_KEY, GIGACHAT_API_URL, GIGACHAT_OAUTH_URL, CERT_PATH,
    YANDEX_OAUTH_TOKEN, YANDEX_FOLDER_ID, YANDEX_API_URL, YANDEX_IAM_URL,
    ACTIVE_AI_MODEL
)

logger = logging.getLogger(__name__)

# GigaChat Auth
access_token = None
token_expiry = None

async def get_access_token():
    """Получает токен доступа через OAuth 2.0 для GigaChat"""
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
                response.raise_for_status()
                token_data = await response.json()
                access_token = token_data["access_token"]
                expires_at_ms = token_data["expires_at"]
                token_expiry = datetime.fromtimestamp(expires_at_ms / 1000) - timedelta(seconds=60)
                logger.info("Токен GigaChat успешно получен")
                return access_token
        except Exception as e:
            logger.error(f"Ошибка при получении токена GigaChat: {str(e)}")
            raise

async def query_gigachat(prompt, max_tokens=2048):
    """Асинхронный запрос к GigaChat API"""
    global access_token
    if not access_token or datetime.now() >= token_expiry:
        await get_access_token()

    ssl_context = ssl.create_default_context(cafile=CERT_PATH)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "GigaChat-Pro",
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
                if response.status == 200:
                    json_response = await response.json()
                    return json_response["choices"][0]["message"]["content"].strip()
                logger.error(f"GigaChat ошибка: {response.status}")
                return f"Ошибка GigaChat: {response.status}"
        except Exception as e:
            logger.error(f"GigaChat соединение ошибка: {str(e)}")
            return f"Ошибка соединения: {str(e)}"

async def retry_query_gigachat(prompt, max_tokens=2048, max_retries=3, delay=5):
    """Асинхронный повтор запроса к GigaChat при ошибке"""
    for attempt in range(max_retries):
        response = await query_gigachat(prompt, max_tokens)
        if "Ошибка" not in response:
            return response
        if attempt < max_retries - 1:
            await asyncio.sleep(delay)
            logger.info(f"Повтор попытки {attempt + 1} для GigaChat")
    return response

# Yandex GPT Auth
yandex_iam_token = None
yandex_token_expiry = None

async def get_yandex_iam_token():
    """Получает IAM-токен для Yandex Cloud"""
    global yandex_iam_token, yandex_token_expiry
    if yandex_iam_token and datetime.now() < yandex_token_expiry:
        return yandex_iam_token

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {YANDEX_OAUTH_TOKEN}"
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(YANDEX_IAM_URL, headers=headers) as response:
                response.raise_for_status()
                token_data = await response.json()
                yandex_iam_token = token_data["iamToken"]
                yandex_token_expiry = datetime.now() + timedelta(hours=1)
                logger.info("Токен Yandex GPT успешно получен")
                return yandex_iam_token
        except Exception as e:
            logger.error(f"Yandex IAM token ошибка: {str(e)}")
            raise

async def query_yandexgpt(prompt, max_tokens=2048):
    """Асинхронный запрос к Yandex GPT API"""
    global yandex_iam_token
    if not yandex_iam_token:
        await get_yandex_iam_token()

    headers = {
        "Authorization": f"Bearer {yandex_iam_token}",
        "x-folder-id": YANDEX_FOLDER_ID,
        "Content-Type": "application/json"
    }
    payload = {
        "model": "general",
        "generationOptions": {
            "maxTokens": max_tokens,
            "temperature": 0.1
        },
        "instructionText": "Ты - учитель-ассистент. Отвечай на русском языке простыми словами, избегай специальных символов и форматирования.",
        "requestText": prompt
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                YANDEX_API_URL,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=600)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data["result"]["alternatives"][0]["text"].strip()
                logger.error(f"Yandex GPT ошибка: {response.status}")
                return f"Ошибка Yandex GPT: {response.status}"
        except Exception as e:
            logger.error(f"Yandex GPT соединение ошибка: {str(e)}")
            return f"Ошибка соединения: {str(e)}"

async def query_ai(prompt, max_tokens=2048):
    """Универсальный метод для запросов к AI"""
    if ACTIVE_AI_MODEL == "gigachat":
        return await retry_query_gigachat(prompt, max_tokens)
    elif ACTIVE_AI_MODEL == "yandexgpt":
        return await query_yandexgpt(prompt, max_tokens)
    else:
        raise ValueError(f"Неизвестная модель AI: {ACTIVE_AI_MODEL}")