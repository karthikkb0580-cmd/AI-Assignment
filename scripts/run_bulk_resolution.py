import argparse
import asyncio

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from ai_pipeline.database.connection import AsyncSessionLocal
from ai_pipeline.database.models import PipelineCheckpoint
from ai_pipeline.services.bulk_resolution import process_batch


WORKER_NAME = "startup_resolution"


async def run(batch_size: int):
    total_processed = 0
    total_resolved = 0
    total_unmatched = 0
    total_skipped = 0
    total_failed = 0

    async with AsyncSessionLocal() as session:

        # Ensure the checkpoint row exists.
        statement = (
            insert(PipelineCheckpoint)
            .values(worker_name=WORKER_NAME)
            .on_conflict_do_nothing(
                index_elements=["worker_name"]
            )
        )

        await session.execute(statement)
        await session.commit()

        while True:
            try:
                # Lock the checkpoint row so only one worker
                # can process this stream at a time.
                result = await session.execute(
                    select(PipelineCheckpoint)
                    .where(
                        PipelineCheckpoint.worker_name == WORKER_NAME
                    )
                    .with_for_update()
                )

                checkpoint = result.scalar_one()

                batch = await process_batch(
                    session=session,
                    batch_size=batch_size,
                    last_created_at=checkpoint.last_created_at,
                    last_id=checkpoint.last_record_id,
                )

                if batch.stats.processed == 0:
                    await session.rollback()
                    break

                # Update checkpoint inside the same transaction.
                checkpoint.last_created_at = batch.last_created_at
                checkpoint.last_record_id = batch.last_id

                await session.commit()

                total_processed += batch.stats.processed
                total_resolved += batch.stats.resolved
                total_unmatched += batch.stats.unmatched
                total_skipped += batch.stats.skipped
                total_failed += batch.stats.failed

                print(
                    f"Batch completed: {batch.stats.processed} records"
                )

            except Exception:
                await session.rollback()
                raise

    print("\nDATABASE-BACKED BULK RESOLUTION SUMMARY")
    print("---------------------------------------")
    print(f"Processed: {total_processed}")
    print(f"Matched:   {total_resolved}")
    print(f"Unmatched: {total_unmatched}")
    print(f"Skipped:   {total_skipped}")
    print(f"Failed:    {total_failed}")


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
    )

    args = parser.parse_args()

    if args.batch_size < 1:
        parser.error("--batch-size must be positive")

    asyncio.run(run(args.batch_size))


if __name__ == "__main__":
    main()