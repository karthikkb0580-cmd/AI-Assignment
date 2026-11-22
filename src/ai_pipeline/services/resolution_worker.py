from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_pipeline.database.models import ExtractionRecord, SourceRecord
from ai_pipeline.services.entity_resolution import resolve_startup


@dataclass
class WorkerStats:
    processed: int = 0
    resolved: int = 0
    unmatched: int = 0
    skipped: int = 0
    failed: int = 0


def get_startup_name(data: dict) -> str | None:

    if not isinstance(data, dict):
        return None

    if data.get("mock") is True:
        return None

    if "results" in data:
        results = data["results"]

        if not isinstance(results, list):
            return None

        candidates = results

    else:
        candidates = [data]

    for item in candidates:

        if not isinstance(item, dict):
            continue

        if item.get("entity_type") != "startup":
            continue

        startup = item.get("startup")

        if not isinstance(startup, dict):
            continue

        name = startup.get("name")

        if not isinstance(name, str):
            continue

        name = name.strip()

        if name:
            return name

    return None

async def process_extractions(
    session: AsyncSession,
    limit: int = 100,
) -> WorkerStats:

    if limit < 1:
        raise ValueError("limit must be positive")

    stats = WorkerStats()

    statement = (
        select(ExtractionRecord, SourceRecord.source_url)
        .join(
            SourceRecord,
            ExtractionRecord.source_record_id == SourceRecord.id,
        )
        .where(ExtractionRecord.status == "completed")
        .order_by(ExtractionRecord.created_at)
        .limit(limit)
    )

    result = await session.execute(statement)

    rows = result.all()

    for extraction, source_url in rows:
        stats.processed += 1

        name = get_startup_name(extraction.extracted_data)

        if not name:
            stats.skipped += 1
            continue

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

        except Exception:
            stats.failed += 1

    return stats