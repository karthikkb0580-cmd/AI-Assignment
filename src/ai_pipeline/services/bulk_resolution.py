from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_pipeline.database.models import (
    ExtractionRecord,
    SourceRecord,
)
from ai_pipeline.services.resolution_worker import (
    WorkerStats,
    get_startup_name,
)
from ai_pipeline.services.entity_resolution import resolve_startup


@dataclass
class BatchResult:
    stats: WorkerStats
    last_created_at: datetime | None
    last_id: UUID | None


async def process_batch(
    session: AsyncSession,
    batch_size: int = 100,
    last_created_at: datetime | None = None,
    last_id: UUID | None = None,
) -> BatchResult:

    if batch_size < 1:
        raise ValueError("batch_size must be positive")

    if (last_created_at is None) != (last_id is None):
        raise ValueError(
            "Checkpoint must contain both created_at and id"
        )

    statement = (
        select(ExtractionRecord, SourceRecord.source_url)
        .join(
            SourceRecord,
            ExtractionRecord.source_record_id == SourceRecord.id,
        )
        .where(ExtractionRecord.status == "completed")
    )

    if last_created_at is not None:
        statement = statement.where(
            or_(
                ExtractionRecord.created_at > last_created_at,
                and_(
                    ExtractionRecord.created_at == last_created_at,
                    ExtractionRecord.id > last_id,
                ),
            )
        )

    statement = (
        statement
        .order_by(
            ExtractionRecord.created_at,
            ExtractionRecord.id,
        )
        .limit(batch_size)
    )

    result = await session.execute(statement)
    rows = result.all()

    stats = WorkerStats()

    newest_created_at = last_created_at
    newest_id = last_id

    for extraction, source_url in rows:
        stats.processed += 1

        name = get_startup_name(extraction.extracted_data)

        if not name:
            stats.skipped += 1
        else:
            try:
                async with session.begin_nested():
                    resolution = await resolve_startup(
                        session=session,
                        name=name,
                        source_url=source_url,
                    )
                    await session.flush()

                if resolution.matched:
                    stats.resolved += 1
                else:
                    stats.unmatched += 1

            except Exception as exc:
                stats.failed += 1
                print(
                    f"Failed extraction {extraction.id}: "
                    f"{type(exc).__name__}: {exc}"
                )

        newest_created_at = extraction.created_at
        newest_id = extraction.id

    return BatchResult(
        stats=stats,
        last_created_at=newest_created_at,
        last_id=newest_id,
    )