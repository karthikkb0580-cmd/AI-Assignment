import asyncio
import logging
from uuid import UUID

from sqlalchemy import select

from ai_pipeline.database.connection import AsyncSessionLocal
from ai_pipeline.database.models import SourceRecord

from ai_pipeline.services.verification_storage import (
    candidate_from_source_record,
    save_verification_result,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)

BATCH_SIZE = 100


async def verify_candidates():
    """
    Read stored GitHub startup candidates,
    calculate preliminary verification scores,
    and save results to PostgreSQL.
    """

    total_processed = 0
    total_failed = 0
    last_id: UUID | None = None

    async with AsyncSessionLocal() as session:

        while True:

            query = (
                select(SourceRecord)
                .where(
                    SourceRecord.record_type == "startup_candidate"
                )
                .order_by(SourceRecord.id)
                .limit(BATCH_SIZE)
            )

            if last_id is not None:
                query = query.where(SourceRecord.id > last_id)

            result = await session.execute(query)

            records = result.scalars().all()

            if not records:
                break

            for record in records:

                last_id = record.id

                try:
                    candidate = candidate_from_source_record(record)

                    async with session.begin_nested():
                        await save_verification_result(
                            session=session,
                            source_record_id=record.id,
                            candidate=candidate,
                        )

                    total_processed += 1

                    logger.info(
                        "Evaluated candidate: %s",
                        candidate.name,
                    )

                except (ValueError, TypeError) as exc:

                    total_failed += 1

                    logger.warning(
                        "Skipping record %s: %s",
                        record.id,
                        exc,
                    )

            await session.commit()

    logger.info("Verification run completed")
    logger.info("Processed: %s", total_processed)
    logger.info("Skipped: %s", total_failed)


if __name__ == "__main__":
    asyncio.run(verify_candidates())