import json

import pytest

from ai_pipeline.llm.client import LLMResponseError
from ai_pipeline.llm.extractor import StructuredExtractor


class FakeLLMClient:
    def __init__(self, response):
        self.response = response

    async def complete(self, messages):
        return json.dumps(self.response)


@pytest.mark.asyncio
async def test_extractor_accepts_valid_evidence():

    client = FakeLLMClient({
        "entity_type": "startup",
        "startup": {
            "name": "NeuralForge"
        },
        "product": None,
        "evidence": [
            {
                "field": "name",
                "quote": "NeuralForge",
                "source_url": "https://example.com"
            }
        ],
        "needs_review": True
    })

    extractor = StructuredExtractor(client)

    results = await extractor.extract(
        text="NeuralForge develops AI tools.",
        source_url="https://example.com"
    )

    assert len(results) == 1
    assert results[0].startup.name == "NeuralForge"


@pytest.mark.asyncio
async def test_extractor_rejects_hallucinated_evidence():

    client = FakeLLMClient({
        "entity_type": "startup",
        "startup": {
            "name": "NeuralForge"
        },
        "product": None,
        "evidence": [
            {
                "field": "name",
                "quote": "FakeCompany",
                "source_url": "https://example.com"
            }
        ],
        "needs_review": True
    })

    extractor = StructuredExtractor(client)

    with pytest.raises(LLMResponseError):
        await extractor.extract(
            text="NeuralForge develops AI tools.",
            source_url="https://example.com"
        )


@pytest.mark.asyncio
async def test_extractor_rejects_missing_evidence():

    client = FakeLLMClient({
        "entity_type": "startup",
        "startup": {
            "name": "NeuralForge"
        },
        "product": None,
        "evidence": [],
        "needs_review": True
    })

    extractor = StructuredExtractor(client)

    with pytest.raises(LLMResponseError):
        await extractor.extract(
            text="NeuralForge develops AI tools.",
            source_url="https://example.com"
        )