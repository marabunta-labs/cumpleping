"""HTTP client for the Telegram API, tolerant to short network hiccups (e.g. PythonAnywhere's outbound proxy)."""
import asyncio
import logging

from telegram.error import NetworkError
from telegram.request import HTTPXRequest

logger = logging.getLogger(__name__)

RETRIES = 3
BACKOFF_SECONDS = 0.5
POOL_SIZE = 16
# Errors that happen *before* Telegram receives the request, so repeating it can't duplicate a message
SAFE_TO_RETRY = ("ProxyError", "ConnectError", "ConnectTimeout")


def is_safe_to_retry(error):
    return any(name in str(error) for name in SAFE_TO_RETRY)


class RetryingRequest(HTTPXRequest):
    """HTTPXRequest that retries connection/proxy failures a few times before giving up."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("connection_pool_size", POOL_SIZE)
        kwargs.setdefault("pool_timeout", 10.0)
        super().__init__(*args, **kwargs)

    async def do_request(self, *args, **kwargs):
        for attempt in range(RETRIES + 1):
            try:
                return await super().do_request(*args, **kwargs)
            except NetworkError as error:
                if attempt == RETRIES or not is_safe_to_retry(error):
                    raise
                delay = BACKOFF_SECONDS * (2 ** attempt)
                logger.warning("Telegram request failed (%s); retrying in %.1fs (%d/%d)", error, delay, attempt + 1, RETRIES)
                await asyncio.sleep(delay)
