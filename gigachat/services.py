import aiohttp
import logging
import asyncio
import ssl
import uuid
from config import GIGACHAT_AUTH_KEY, GIGACHAT_API_URL, GIGACHAT_OAUTH_URL, CERT_PATH
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

GIGACHAT_API_TIMEOUT_SECONDS = 120
GIGACHAT_TOTAL_TIMEOUT_SECONDS = 180

access_token = None
token_expiry = None


class GigaChatError(RuntimeError):
    """A GigaChat authentication or response error that should not be retried."""


class RetryableGigaChatError(GigaChatError):
    """A transient GigaChat error that can be retried."""


def _is_retryable_status(status: int) -> bool:
    return status in {408, 425, 429} or 500 <= status < 600


async def get_access_token():
    """Obtain an access token using OAuth 2.0"""
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
        "scope": "GIGACHAT_API_PERS"
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
                logger.info(f"Статус ответа OAuth: {response.status}")
                response.raise_for_status()
                token_data = await response.json()
                access_token = token_data["access_token"]
                expires_at_ms = token_data["expires_at"]
                expires_at_seconds = expires_at_ms / 1000
                token_expiry = datetime.fromtimestamp(expires_at_seconds) - timedelta(seconds=60)
                logger.info("Токен успешно получен")
                return access_token
        except aiohttp.ClientResponseError as e:
            logger.error("Ошибка OAuth (HTTP %s)", e.status)
            if _is_retryable_status(e.status):
                raise RetryableGigaChatError("Временная ошибка авторизации GigaChat") from e
            raise GigaChatError("Не удалось авторизоваться в GigaChat") from e
        except asyncio.TimeoutError as e:
            logger.error("Истекло время ожидания OAuth")
            raise RetryableGigaChatError("Истекло время ожидания авторизации GigaChat") from e
        except aiohttp.ClientError as e:
            logger.error("Ошибка соединения OAuth (%s)", type(e).__name__)
            raise RetryableGigaChatError("Временная ошибка соединения с GigaChat") from e
        except (KeyError, TypeError, ValueError) as e:
            logger.error("Некорректный ответ OAuth (%s)", type(e).__name__)
            raise GigaChatError("GigaChat вернул некорректный ответ авторизации") from e

async def query_gigachat(prompt, max_tokens=2048):
    """Send an asynchronous request to the GigaChat API"""
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
                timeout=aiohttp.ClientTimeout(total=GIGACHAT_API_TIMEOUT_SECONDS)
            ) as response:
                logger.info(f"Status code API: {response.status}")
                if response.status != 200:
                    logger.error("Ошибка API GigaChat (HTTP %s)", response.status)
                    if _is_retryable_status(response.status):
                        raise RetryableGigaChatError(
                            f"Временная ошибка GigaChat (HTTP {response.status})"
                        )
                    raise GigaChatError(
                        f"GigaChat отклонил запрос (HTTP {response.status})"
                    )

                try:
                    json_response = await response.json()
                except (aiohttp.ContentTypeError, ValueError) as e:
                    raise GigaChatError("GigaChat вернул некорректный JSON") from e

                try:
                    choices = json_response["choices"]
                    text = choices[0]["message"]["content"].strip()
                except (AttributeError, IndexError, KeyError, TypeError) as e:
                    raise GigaChatError("GigaChat вернул ответ неизвестного формата") from e

                if not text:
                    raise GigaChatError("GigaChat вернул пустой ответ")

                logger.debug("Ответ API получен (длина=%d)", len(text))
                return text
        except GigaChatError:
            raise
        except asyncio.TimeoutError as e:
            logger.error("Истекло время ожидания API GigaChat")
            raise RetryableGigaChatError("Истекло время ожидания ответа GigaChat") from e
        except aiohttp.ClientResponseError as e:
            logger.error("Ошибка ответа API GigaChat (HTTP %s)", e.status)
            if _is_retryable_status(e.status):
                raise RetryableGigaChatError(
                    f"Временная ошибка GigaChat (HTTP {e.status})"
                ) from e
            raise GigaChatError(f"GigaChat отклонил запрос (HTTP {e.status})") from e
        except aiohttp.ClientError as e:
            logger.error("Ошибка соединения с API GigaChat (%s)", type(e).__name__)
            raise RetryableGigaChatError("Временная ошибка соединения с GigaChat") from e

async def retry_query_gigachat(
    prompt,
    max_tokens=2048,
    max_retries=3,
    delay=5,
    total_timeout=GIGACHAT_TOTAL_TIMEOUT_SECONDS,
):
    """Retry transient failures within the overall time limit."""
    if max_retries < 1:
        raise ValueError("max_retries должен быть не меньше 1")
    if delay < 0:
        raise ValueError("delay не может быть отрицательным")
    if total_timeout <= 0:
        raise ValueError("total_timeout должен быть больше нуля")

    deadline = asyncio.get_running_loop().time() + total_timeout
    last_error = None
    for attempt in range(max_retries):
        remaining = deadline - asyncio.get_running_loop().time()
        if remaining <= 0:
            raise RetryableGigaChatError(
                "Превышено общее время ожидания ответа GigaChat"
            ) from last_error

        try:
            return await asyncio.wait_for(
                query_gigachat(prompt, max_tokens),
                timeout=remaining,
            )
        except (RetryableGigaChatError, asyncio.TimeoutError) as error:
            last_error = error
            if attempt + 1 == max_retries:
                raise RetryableGigaChatError(
                    "Не удалось получить ответ GigaChat после повторных запросов"
                ) from error

            wait_seconds = delay * (2 ** attempt)
            remaining = deadline - asyncio.get_running_loop().time()
            if wait_seconds >= remaining:
                raise RetryableGigaChatError(
                    "Превышено общее время ожидания ответа GigaChat"
                ) from error

            logger.info("Повтор запроса GigaChat через %s секунд", wait_seconds)
            await asyncio.sleep(wait_seconds)
