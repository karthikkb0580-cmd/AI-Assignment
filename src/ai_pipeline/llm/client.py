import asyncio
import logging
import random
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone

import httpx


logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Base exception for LLM failures."""


class LLMRateLimitError(LLMError):
    """Raised when rate limits are exhausted."""


class LLMContextLengthError(LLMError):
    """Raised when the request is too large."""


class LLMResponseError(LLMError):
    """Raised for invalid or unsuccessful responses."""


class ResilientLLMClient:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        max_retries: int = 4,
        timeout: float = 60.0,
        http_client: httpx.AsyncClient | None = None,
    ):
        if not base_url.startswith("https://"):
            raise ValueError("LLM base_url must use HTTPS")

        if not api_key:
            raise ValueError("LLM API key is required")

        if not model:
            raise ValueError("LLM model is required")

        if max_retries < 0:
            raise ValueError("max_retries cannot be negative")

        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.max_retries = max_retries
        self.timeout = timeout
        self._http_client = http_client

    async def complete(
        self,
        messages: list[dict],
    ) -> str:
        """
        Send messages to the LLM.

        Automatically retries:
        - HTTP 429
        - HTTP 500
        - HTTP 502
        - HTTP 503
        - HTTP 504
        - Network errors
        - Timeouts

        HTTP 413 raises LLMContextLengthError so the
        extraction layer can split the input.
        """

        endpoint = f"{self.base_url}/chat/completions"

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async def send(client: httpx.AsyncClient) -> str:

            for attempt in range(self.max_retries + 1):

                try:
                    logger.info(
                        "Sending LLM request | model=%s | attempt=%s/%s",
                        self.model,
                        attempt + 1,
                        self.max_retries + 1,
                    )

                    response = await client.post(
                        endpoint,
                        json=payload,
                        headers=headers,
                    )

                except (
                    httpx.TimeoutException,
                    httpx.NetworkError,
                ) as exc:

                    if attempt >= self.max_retries:
                        raise LLMResponseError(
                            "LLM network retries exhausted"
                        ) from exc

                    delay = self.calculate_retry_delay(attempt)

                    logger.warning(
                        "LLM network error: %s. "
                        "Retrying in %.2f seconds.",
                        type(exc).__name__,
                        delay,
                    )

                    await asyncio.sleep(delay)
                    continue

                status_code = response.status_code

                # Request is too large
                if status_code == 413:
                    raise LLMContextLengthError(
                        "LLM request exceeded provider context limit"
                    )

                # Rate limiting
                if status_code == 429:

                    if attempt >= self.max_retries:
                        raise LLMRateLimitError(
                            "LLM rate limit retries exhausted"
                        )

                    delay = self.get_retry_delay(
                        response,
                        attempt,
                    )

                    logger.warning(
                        "LLM rate limited (429). "
                        "Retrying in %.2f seconds.",
                        delay,
                    )

                    await asyncio.sleep(delay)
                    continue

                # Temporary provider failures
                if status_code in {500, 502, 503, 504}:

                    if attempt >= self.max_retries:
                        raise LLMResponseError(
                            f"LLM provider unavailable after "
                            f"{self.max_retries + 1} attempts: "
                            f"HTTP {status_code}"
                        )

                    delay = self.get_retry_delay(
                        response,
                        attempt,
                    )

                    logger.warning(
                        "LLM temporary failure HTTP %s. "
                        "Retrying in %.2f seconds.",
                        status_code,
                        delay,
                    )

                    await asyncio.sleep(delay)
                    continue

                # Non-retryable HTTP errors
                if status_code >= 400:

                    error_detail = response.text[:500]

                    raise LLMResponseError(
                        f"LLM request failed: HTTP {status_code}. "
                        f"Details: {error_detail}"
                    )

                # Successful HTTP response
                try:
                    data = response.json()

                    content = data["choices"][0]["message"]["content"]

                    if not isinstance(content, str):
                        raise ValueError(
                            "LLM response content is not a string"
                        )

                    logger.info(
                        "LLM request successful | model=%s",
                        self.model,
                    )

                    return content

                except (
                    ValueError,
                    KeyError,
                    IndexError,
                    TypeError,
                ) as exc:

                    raise LLMResponseError(
                        "Invalid LLM response structure"
                    ) from exc

            raise LLMResponseError(
                "LLM retries exhausted"
            )

        # Use injected HTTP client for testing
        if self._http_client is not None:
            return await send(self._http_client)

        # Create HTTP client for normal operation
        async with httpx.AsyncClient(
            timeout=self.timeout,
            trust_env=False,
        ) as client:
            return await send(client)

    @staticmethod
    def calculate_retry_delay(
        attempt: int,
        base_delay: float = 2.0,
        max_delay: float = 60.0,
    ) -> float:
        """
        Exponential backoff with jitter.

        Example approximate delays:
        Attempt 1: 2 seconds
        Attempt 2: 4 seconds
        Attempt 3: 8 seconds
        Attempt 4: 16 seconds
        """

        exponential_delay = min(
            base_delay * (2 ** attempt),
            max_delay,
        )

        jitter = random.uniform(
            0,
            exponential_delay * 0.25,
        )

        return exponential_delay + jitter

    @classmethod
    def get_retry_delay(
        cls,
        response: httpx.Response,
        attempt: int,
    ) -> float:
        """
        Respect Retry-After when provided.

        Otherwise use exponential backoff.
        """

        retry_after = response.headers.get("Retry-After")

        if retry_after:

            try:
                return max(0.0, float(retry_after))

            except ValueError:
                try:
                    retry_date = parsedate_to_datetime(
                        retry_after
                    )

                    if retry_date.tzinfo is None:
                        retry_date = retry_date.replace(
                            tzinfo=timezone.utc
                        )

                    delay = (
                        retry_date
                        - datetime.now(timezone.utc)
                    ).total_seconds()

                    return max(0.0, delay)

                except (ValueError, TypeError, OverflowError):
                    pass

        return cls.calculate_retry_delay(attempt)