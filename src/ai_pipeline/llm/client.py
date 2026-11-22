import asyncio
import random

import httpx


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

                    await self._backoff(attempt)
                    continue

                if response.status_code == 413:
                    raise LLMContextLengthError(
                        "LLM request exceeded provider limit"
                    )

                if response.status_code == 429:
                    if attempt >= self.max_retries:
                        raise LLMRateLimitError(
                            "LLM rate limit retries exhausted"
                        )

                    await self._backoff(attempt)
                    continue

                if response.status_code in {
                    500, 502, 503, 504
                }:
                    if attempt >= self.max_retries:
                        raise LLMResponseError(
                            f"Provider unavailable: {response.status_code}"
                        )

                    await self._backoff(attempt)
                    continue

                if response.status_code >= 400:
                    raise LLMResponseError(
                        f"LLM request failed: HTTP {response.status_code}"
                    )

                try:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]

                    if not isinstance(content, str):
                        raise ValueError("Content is not a string")

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

            raise LLMResponseError("Retries exhausted")

        if self._http_client is not None:
            return await send(self._http_client)

        async with httpx.AsyncClient(
            timeout=self.timeout,
            trust_env=False,
        ) as client:
            return await send(client)

    @staticmethod
    async def _backoff(attempt: int) -> None:
        delay = min(
            2 ** attempt + random.uniform(0, 0.5),
            30,
        )
        await asyncio.sleep(delay)