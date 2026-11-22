import json

import httpx
import pytest

from ai_pipeline.llm.client import (
    LLMContextLengthError,
    ResilientLLMClient,
)
from ai_pipeline.llm.extractor import StructuredExtractor


BASE_URL = "https://llm.example.test/v1"


def make_response(content: str):
    return {
        "choices": [
            {
                "message": {
                    "content": content
                }
            }
        ]
    }


@pytest.mark.asyncio
async def test_llm_success():
    def handler(request):
        return httpx.Response(
            200,
            json=make_response('{"ok": true}'),
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    ) as http_client:

        client = ResilientLLMClient(
            api_key="test-key",
            base_url=BASE_URL,
            model="test-model",
            http_client=http_client,
        )

        result = await client.complete(
            [{"role": "user", "content": "Hello"}]
        )

    assert result == '{"ok": true}'


@pytest.mark.asyncio
async def test_llm_rate_limit_retry():
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1

        if calls == 1:
            return httpx.Response(429)

        return httpx.Response(
            200,
            json=make_response('{"ok": true}'),
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    ) as http_client:

        client = ResilientLLMClient(
            api_key="test-key",
            base_url=BASE_URL,
            model="test-model",
            max_retries=2,
            http_client=http_client,
        )

        result = await client.complete(
            [{"role": "user", "content": "Hello"}]
        )

    assert calls == 2
    assert result == '{"ok": true}'


@pytest.mark.asyncio
async def test_llm_413_error():
    def handler(request):
        return httpx.Response(413)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    ) as http_client:

        client = ResilientLLMClient(
            api_key="test-key",
            base_url=BASE_URL,
            model="test-model",
            http_client=http_client,
        )

        with pytest.raises(LLMContextLengthError):
            await client.complete(
                [{"role": "user", "content": "Large input"}]
            )


@pytest.mark.asyncio
async def test_structured_extraction():
    source_text = (
        "ExampleAI builds AI tools for developers."
    )

    output = {
        "entity_type": "startup",
        "startup": {
            "name": "ExampleAI",
            "description": "Builds AI tools for developers.",
            "website": None,
            "industry": None,
            "headquarters": None,
            "founded_year": None,
        },
        "product": None,
        "evidence": [
            {
                "field": "name",
                "quote": "ExampleAI",
                "source_url": "https://example.test/startup",
            }
        ],
        "needs_review": True,
    }

    def handler(request):
        return httpx.Response(
            200,
            json=make_response(json.dumps(output)),
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    ) as http_client:

        client = ResilientLLMClient(
            api_key="test-key",
            base_url=BASE_URL,
            model="test-model",
            http_client=http_client,
        )

        extractor = StructuredExtractor(client)

        results = await extractor.extract(
            text=source_text,
            source_url="https://example.test/startup",
        )

    assert len(results) == 1
    assert results[0].startup.name == "ExampleAI"
    assert results[0].needs_review is True