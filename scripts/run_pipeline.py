import argparse
import asyncio
import logging

from sqlalchemy import text

from ai_pipeline.database.connection import (
    AsyncSessionLocal,
    engine,
)

from ai_pipeline.services.resolution_jobs import (
    create_missing_jobs,
    process_resolution_jobs,
)

from run_extraction import run_extraction


LOCK_ID = 16012026

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("pipeline")


async def run_resolution(batch_size: int) -> dict:
    """
    Create and process resolution jobs.

    Each batch is committed independently so completed
    batches survive process interruption.
    """

    totals = {
        "processed": 0,
        "matched": 0,
        "unmatched": 0,
        "skipped": 0,
        "retry": 0,
        "failed": 0,
    }

    async with AsyncSessionLocal() as session:
        try:
            created = await create_missing_jobs(session)
            await session.commit()

            logger.info(
                "Resolution jobs created: %s",
                created,
            )

            while True:
                stats = await process_resolution_jobs(
                    session=session,
                    batch_size=batch_size,
                )

                await session.commit()

                if stats["processed"] == 0:
                    break

                for key in totals:
                    totals[key] += stats[key]

                logger.info(
                    "Resolution batch: %s",
                    stats,
                )

        except Exception:
            await session.rollback()
            logger.exception(
                "Resolution processing failed"
            )
            raise

    return totals


async def run_pipeline(args) -> bool:
    """
    Execute pipeline with an exclusive advisory lock.

    The lock is acquired and released using the same
    pinned PostgreSQL connection.
    """

    logger.info("=" * 60)
    logger.info("AI INTELLIGENCE PIPELINE")
    logger.info("=" * 60)

    async with engine.connect() as lock_connection:
        acquired = False

        try:
            result = await lock_connection.execute(
                text(
                    "SELECT pg_try_advisory_lock(:lock_id)"
                ),
                {"lock_id": LOCK_ID},
            )

            acquired = bool(result.scalar_one())

            if not acquired:
                logger.warning(
                    "Another pipeline instance is running. "
                    "Skipping this execution."
                )
                return False

            logger.info(
                "Pipeline advisory lock acquired"
            )

            # ------------------------------------------------
            # Stage 1 - Extraction
            # ------------------------------------------------

            logger.info("[1/2] Starting extraction")

            await run_extraction(
                limit=args.limit,
                mock=not args.real,
                max_attempts=args.max_attempts,
                source_name=args.source_name,
            )

            logger.info(
                "Extraction stage completed"
            )

            # ------------------------------------------------
            # Stage 2 - Resolution
            # ------------------------------------------------

            logger.info(
                "[2/2] Starting entity resolution"
            )

            totals = await run_resolution(
                args.batch_size
            )

            logger.info("PIPELINE SUMMARY")

            for key, value in totals.items():
                logger.info("%s: %s", key, value)

            logger.info(
                "Pipeline completed successfully"
            )

            return True

        except Exception:
            logger.exception(
                "Pipeline execution failed"
            )
            raise

        finally:
            if acquired:
                try:
                    result = await lock_connection.execute(
                        text(
                            "SELECT pg_advisory_unlock(:lock_id)"
                        ),
                        {"lock_id": LOCK_ID},
                    )

                    released = bool(result.scalar_one())

                    if released:
                        logger.info(
                            "Pipeline advisory lock released"
                        )
                    else:
                        logger.error(
                            "Advisory lock release returned false"
                        )

                except Exception:
                    logger.exception(
                        "Failed to release pipeline lock"
                    )

                    # Invalidate the connection to prevent
                    # returning an uncertain lock state
                    # to the connection pool.
                    await lock_connection.invalidate()


def parse_args():
    parser = argparse.ArgumentParser(
        description="AI Intelligence Pipeline"
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=10,
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
    )

    parser.add_argument(
        "--max-attempts",
        type=int,
        default=3,
    )

    parser.add_argument(
        "--source-name",
        default=None,
    )

    parser.add_argument(
        "--real",
        action="store_true",
        help="Enable real LLM extraction",
    )

    args = parser.parse_args()

    if args.limit < 1:
        parser.error(
            "--limit must be positive"
        )

    if args.batch_size < 1:
        parser.error(
            "--batch-size must be positive"
        )

    if args.max_attempts < 1:
        parser.error(
            "--max-attempts must be positive"
        )

    return args


def main():
    args = parse_args()

    asyncio.run(
        run_pipeline(args)
    )


if __name__ == "__main__":
    main()