import asyncio
import logging

import aiohttp

from config import HF_API_TOKEN, HF_API_URL

logger = logging.getLogger(__name__)

HF_API_TIMEOUT_SECONDS = 120
HF_TOTAL_TIMEOUT_SECONDS = 180


class HuggingFaceError(RuntimeError):
    """A permanent Hugging Face request or response error."""


class RetryableHuggingFaceError(HuggingFaceError):
    """A transient Hugging Face error that can be retried."""


def _is_retryable_status(status: int) -> bool:
    return status in {408, 425, 429} or 500 <= status < 600


def _clean_generated_text(text: str) -> str:
    sentences = text.split(". ")
    unique_sentences = []
    for sentence in sentences:
        if sentence and sentence not in unique_sentences:
            unique_sentences.append(sentence)

    cleaned_text = ". ".join(unique_sentences)
    if cleaned_text and not cleaned_text.endswith("."):
        cleaned_text += "."
    return cleaned_text


async def query_hugging_face(prompt, max_length=150):
    """Request text generation from Hugging Face asynchronously."""
    headers = {
        "Authorization": f"Bearer {HF_API_TOKEN}",
        "x-wait-for-model": "true",
    }
    payload = {
        "inputs": prompt,
        "parameters": {"max_length": max_length, "return_full_text": False},
    }
    logger.info("Hugging Face request started (prompt_length=%d)", len(prompt))

    timeout = aiohttp.ClientTimeout(total=HF_API_TIMEOUT_SECONDS)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(HF_API_URL, headers=headers, json=payload) as response:
                if response.status != 200:
                    logger.error("Hugging Face request failed (HTTP %s)", response.status)
                    if _is_retryable_status(response.status):
                        raise RetryableHuggingFaceError(
                            f"Временная ошибка Hugging Face (HTTP {response.status})"
                        )
                    raise HuggingFaceError(
                        f"Hugging Face отклонил запрос (HTTP {response.status})"
                    )

                try:
                    result = await response.json()
                except aiohttp.ClientError as error:
                    raise RetryableHuggingFaceError(
                        "Не удалось получить полный ответ Hugging Face"
                    ) from error
                except ValueError as error:
                    raise HuggingFaceError(
                        "Hugging Face вернул некорректный JSON"
                    ) from error

                try:
                    generated_text = result[0]["generated_text"].strip()
                except (AttributeError, IndexError, KeyError, TypeError) as error:
                    raise HuggingFaceError(
                        "Hugging Face вернул ответ неизвестного формата"
                    ) from error

                if not generated_text:
                    raise HuggingFaceError("Hugging Face вернул пустой ответ")

                cleaned_text = _clean_generated_text(generated_text)
                logger.debug(
                    "Hugging Face response received (length=%d)", len(cleaned_text)
                )
                return cleaned_text
    except HuggingFaceError:
        raise
    except asyncio.TimeoutError as error:
        logger.error("Hugging Face request timed out")
        raise RetryableHuggingFaceError(
            "Истекло время ожидания ответа Hugging Face"
        ) from error
    except aiohttp.ClientError as error:
        logger.error("Hugging Face request failed (%s)", type(error).__name__)
        raise RetryableHuggingFaceError(
            "Временная ошибка соединения с Hugging Face"
        ) from error


async def retry_query_hugging_face(
    prompt,
    max_length=150,
    max_retries=3,
    delay=5,
    total_timeout=HF_TOTAL_TIMEOUT_SECONDS,
):
    """Retry transient failures within the overall time limit."""
    if max_retries < 1:
        raise ValueError("max_retries должен быть не меньше 1")
    if delay < 0:
        raise ValueError("delay не может быть отрицательным")
    if total_timeout <= 0:
        raise ValueError("total_timeout должен быть больше нуля")

    loop = asyncio.get_running_loop()
    deadline = loop.time() + total_timeout
    last_error = None

    for attempt in range(max_retries):
        remaining = deadline - loop.time()
        if remaining <= 0:
            raise RetryableHuggingFaceError(
                "Превышено общее время ожидания ответа Hugging Face"
            ) from last_error

        try:
            return await asyncio.wait_for(
                query_hugging_face(prompt, max_length),
                timeout=remaining,
            )
        except (RetryableHuggingFaceError, asyncio.TimeoutError) as error:
            last_error = error
            if attempt + 1 == max_retries:
                raise RetryableHuggingFaceError(
                    "Не удалось получить ответ Hugging Face после повторных запросов"
                ) from error

            wait_seconds = delay * (2 ** attempt)
            remaining = deadline - loop.time()
            if wait_seconds >= remaining:
                raise RetryableHuggingFaceError(
                    "Превышено общее время ожидания ответа Hugging Face"
                ) from error

            logger.info("Retrying Hugging Face request in %s seconds", wait_seconds)
            await asyncio.sleep(wait_seconds)
