from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, literal, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ai_pipeline.database.models import ExtractionRecord, ResolutionJob, SourceRecord
from ai_pipeline.services.entity_resolution import resolve_startup
from ai_pipeline.services.resolution_worker import get_startup_name

MAX_ATTEMPTS = 4
BASE_RETRY_SECONDS = 30


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


async def create_missing_jobs(session: AsyncSession) -> int:
    """Insert a pending job for each completed extraction, without duplicates."""
    now = now_utc()
    source = (
        select(
            func.gen_random_uuid(),
            ExtractionRecord.id,
            literal("pending"),
            literal(0),
            literal(now),
            literal(now),
        )
        .where(
    ExtractionRecord.status == "completed",
    ExtractionRecord.extractor_version == "llm-v1",
    ExtractionRecord.extracted_data.is_not(None),
    ExtractionRecord.extracted_data["mock"].as_boolean().is_distinct_from(True),
)
    )
    statement = (
        insert(ResolutionJob)
        .from_select(
            ["id", "extraction_id", "status", "attempt_count", "created_at", "updated_at"],
            source,
            include_defaults=False,
        )
        .on_conflict_do_nothing(index_elements=["extraction_id"])
    )
    result = await session.execute(statement)
    return result.rowcount


async def process_resolution_jobs(session: AsyncSession, batch_size: int = 100) -> dict[str, int]:
    """Process due jobs. Caller must commit/rollback the surrounding transaction."""
    if batch_size < 1:
        raise ValueError("batch_size must be positive")

    now = now_utc()
    statement = (
        select(ResolutionJob, ExtractionRecord, SourceRecord.source_url)
        .join(ExtractionRecord, ResolutionJob.extraction_id == ExtractionRecord.id)
        .join(SourceRecord, ExtractionRecord.source_record_id == SourceRecord.id)
        .where(
    ExtractionRecord.status == "completed",
    ExtractionRecord.extractor_version == "llm-v1",
    ExtractionRecord.extracted_data.is_not(None),
    ExtractionRecord.extracted_data["mock"].as_boolean().is_distinct_from(True),
    or_(
                ResolutionJob.status == "pending",
                and_(
                    ResolutionJob.status == "retry",
                    ResolutionJob.next_retry_at <= now,
                ),
            ),
        )
        .order_by(ResolutionJob.created_at, ResolutionJob.id)
        .limit(batch_size)
        .with_for_update(of=ResolutionJob, skip_locked=True)
    )
    rows = (await session.execute(statement)).all()
    stats = {key: 0 for key in ("processed", "matched", "unmatched", "skipped", "retry", "failed")}

    for job, extraction, source_url in rows:
        stats["processed"] += 1
        name = get_startup_name(extraction.extracted_data)
        if not name:
            job.status = "skipped"
            job.last_error = None
            job.next_retry_at = None
            job.updated_at = now_utc()
            stats["skipped"] += 1
            continue

        job.attempt_count += 1
        try:
            async with session.begin_nested():
                resolution = await resolve_startup(
                    session=session, name=name, source_url=source_url
                )
                await session.flush()
        except Exception as exc:
            job.last_error = f"{type(exc).__name__}: {exc}"[:2000]
            job.updated_at = now_utc()
            if job.attempt_count >= MAX_ATTEMPTS:
                job.status = "failed"
                job.next_retry_at = None
                stats["failed"] += 1
            else:
                delay = BASE_RETRY_SECONDS * (2 ** (job.attempt_count - 1))
                job.status = "retry"
                job.next_retry_at = now_utc() + timedelta(seconds=delay)
                stats["retry"] += 1
        else:
            job.status = "completed"
            job.last_error = None
            job.next_retry_at = None
            job.updated_at = now_utc()
            stats["matched" if resolution.matched else "unmatched"] += 1

    await session.flush()
    return stats
