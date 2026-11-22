from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_pipeline.database.models import ExtractionRecord


EXTRACTOR_VERSION = "v1"


async def get_extraction_record(
    session: AsyncSession,
    source_record_id: UUID,
    content_hash: str,
    extractor_version: str = EXTRACTOR_VERSION,
) -> ExtractionRecord | None:

    statement = select(ExtractionRecord).where(
        ExtractionRecord.source_record_id == source_record_id,
        ExtractionRecord.content_hash == content_hash,
        ExtractionRecord.extractor_version == extractor_version,
    )

    result = await session.execute(statement)

    return result.scalar_one_or_none()


async def save_extraction_success(
    session: AsyncSession,
    source_record_id: UUID,
    content_hash: str,
    extracted_data: dict,
    extractor_version: str = EXTRACTOR_VERSION,
) -> ExtractionRecord:

    record = await get_extraction_record(
        session=session,
        source_record_id=source_record_id,
        content_hash=content_hash,
        extractor_version=extractor_version,
    )

    if record is None:
        record = ExtractionRecord(
            source_record_id=source_record_id,
            content_hash=content_hash,
            extractor_version=extractor_version,
        )

        session.add(record)

    record.status = "completed"
    record.extracted_data = extracted_data
    record.error_message = None
    record.attempt_count = (record.attempt_count or 0) + 1
    record.updated_at = datetime.now(timezone.utc)

    await session.flush()

    return record


async def save_extraction_failure(
    session: AsyncSession,
    source_record_id: UUID,
    content_hash: str,
    error_message: str,
    extractor_version: str = EXTRACTOR_VERSION,
) -> ExtractionRecord:

    record = await get_extraction_record(
        session=session,
        source_record_id=source_record_id,
        content_hash=content_hash,
        extractor_version=extractor_version,
    )

    if record is None:
        record = ExtractionRecord(
            source_record_id=source_record_id,
            content_hash=content_hash,
            extractor_version=extractor_version,
        )

        session.add(record)

    record.status = "failed"
    record.extracted_data = None
    record.error_message = error_message[:2000]
    record.attempt_count = (record.attempt_count or 0) + 1
    record.updated_at = datetime.now(timezone.utc)

    await session.flush()

    return record