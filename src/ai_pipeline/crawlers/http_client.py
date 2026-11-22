import asyncio
import logging

import httpx

logger = logging.getLogger(__name__)


class AsyncHTTPClient:
    def __init__(
        self,
        timeout: float = 30.0,
        max_retries: int = 4,
        concurrency: int = 5,
        user_agent: str = "AIIntelligencePipeline/0.1 (research project)",
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.semaphore = asyncio.Semaphore(concurrency)

        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            follow_redirects=True,
            headers={
                "User-Agent": user_agent,
                "Accept": "application/atom+xml, application/xml, application/json",
            },
        )

    async def get(
        self,
        url: str,
        params: dict | None = None,
    ) -> httpx.Response:
        async with self.semaphore:
            for attempt in range(self.max_retries + 1):
                try:
                    response = await self.client.get(
                        url,
                        params=params,
                    )

                    if response.status_code in (429, 500, 502, 503, 504):
                        if attempt == self.max_retries:
                            response.raise_for_status()

                        retry_after = response.headers.get("Retry-After")
                        delay = min(2**attempt, 30)

                        if retry_after:
                            try:
                                delay = min(float(retry_after), 60)
                            except ValueError:
                                pass

                        logger.warning(
                            "HTTP %s from %s; retrying in %ss",
                            response.status_code,
                            url,
                            delay,
                        )

                        await asyncio.sleep(delay)
                        continue

                    response.raise_for_status()
                    return response

                except (
                    httpx.TimeoutException,
                    httpx.NetworkError,
                ):
                    if attempt == self.max_retries:
                        raise

                    await asyncio.sleep(min(2**attempt, 30))

        raise RuntimeError("HTTP request failed")

    async def close(self):
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.close()