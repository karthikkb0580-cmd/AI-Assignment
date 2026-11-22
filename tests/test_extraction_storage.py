import uuid

import pytest
from sqlalchemy import select

from ai_pipeline.database.connection import AsyncSessionLocal
from ai_pipeline.database.models import ExtractionRecord, SourceRecord
from ai_pipeline.services.extraction_storage import (
    save_extraction_failure,
    save_extraction_success,
)


@pytest.mark.asyncio
async def test_extraction_storage():
    source_id = uuid.uuid4()

    async with AsyncSessionLocal() as session:
        source = SourceRecord(
            id=source_id,
            source_name="storage_test",
            source_url=f"https://example.test/{source_id}",
            record_type="startup_candidate",
            raw_content="ExampleAI builds developer tools.",
            raw_metadata={},
            content_hash="a" * 64,
            processing_status="pending",
        )

        session.add(source)
        await session.flush()

        saved = await save_extraction_success(
            session=session,
            source_record_id=source_id,
            content_hash="a" * 64,
            extracted_data={
                "results": [],
                "needs_review": True,
            },
        )

        assert saved.status == "completed"
        assert saved.attempt_count == 1

        await save_extraction_failure(
            session=session,
            source_record_id=source_id,
            content_hash="a" * 64,
            error_message="Simulated failure",
        )

        result = await session.execute(
            select(ExtractionRecord).where(
                ExtractionRecord.source_record_id == source_id
            )
        )

        record = result.scalar_one()

        assert record.status == "failed"
        assert record.attempt_count == 2
        assert record.error_message == "Simulated failure"

        # Roll back test data instead of saving it permanently.
        await session.rollback()