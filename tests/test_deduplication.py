import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from ai_pipeline.services.deduplication import (
    find_existing_startup,
)


@pytest.mark.asyncio
async def test_existing_startup_found():

    startup = MagicMock()

    startup.id = uuid.uuid4()
    startup.name = "NeuralForge AI"

    result_proxy = MagicMock()
    result_proxy.scalar_one_or_none.return_value = startup

    session = AsyncMock()
    session.execute.return_value = result_proxy

    result = await find_existing_startup(
        session,
        "  NEURALFORGE AI  ",
    )

    assert result.matched is True
    assert result.canonical_name == "NeuralForge AI"
    assert result.match_method == "exact_normalized_name"
    assert result.confidence_score == 1.0


@pytest.mark.asyncio
async def test_startup_not_found():

    result_proxy = MagicMock()
    result_proxy.scalar_one_or_none.return_value = None

    session = AsyncMock()
    session.execute.return_value = result_proxy

    result = await find_existing_startup(
        session,
        "Unknown Startup",
    )

    assert result.matched is False
    assert result.startup_id is None
    assert result.match_method == "no_match"


@pytest.mark.asyncio
async def test_invalid_startup_name():

    session = AsyncMock()

    result = await find_existing_startup(
        session,
        "   ",
    )

    assert result.matched is False
    assert result.match_method == "invalid_name"

    session.execute.assert_not_called()
    