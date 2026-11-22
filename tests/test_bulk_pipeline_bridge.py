import pytest

from ai_pipeline.services.bulk_pipeline_bridge import (
    build_metadata,
    build_raw_content,
    transfer_bulk_records,
)


def test_build_raw_content():
    content = build_raw_content(
        name="Example AI",
        website="https://example.com",
    )

    assert "Example AI" in content
    assert "https://example.com" in content


def test_build_raw_content_missing_website():
    content = build_raw_content(
        name="Example AI",
        website=None,
    )

    assert "Not available" in content


def test_build_metadata():
    metadata = build_metadata(
        bulk_id=42,
        name="Example AI",
        website="https://example.com",
    )

    assert metadata["bulk_record_id"] == 42
    assert metadata["name"] == "Example AI"
    assert metadata["origin"] == "bulk_csv_ingestion"
    assert metadata["verified_company"] is False


@pytest.mark.asyncio
async def test_invalid_batch_size():
    with pytest.raises(ValueError):
        await transfer_bulk_records(
            database_url="postgresql://invalid",
            batch_size=0,
        )


@pytest.mark.asyncio
async def test_invalid_after_id():
    with pytest.raises(ValueError):
        await transfer_bulk_records(
            database_url="postgresql://invalid",
            after_id=-1,
        )