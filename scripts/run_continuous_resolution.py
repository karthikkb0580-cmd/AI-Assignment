"""
Step 13.6 — Continuous Resolution Worker

Features:
- Continuous polling
- Automatic job creation
- Batch processing
- Scheduled retries
- Error recovery
- Graceful shutdown
- Structured logging
"""

import argparse
import asyncio
import logging
import signal

from ai_pipeline.database.connection import AsyncSessionLocal
from ai_pipeline.services.resolution_jobs import (
    create_missing_jobs,
    process_resolution_jobs,
)


logger = logging.getLogger("resolution_worker")


def configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s | %(levelname)s | "
            "%(name)s | %(message)s"
        ),
    )


class ContinuousResolutionWorker:

    def __init__(
        self,
        batch_size: int = 100,
        poll_interval: float = 10.0,
    ):
        if batch_size < 1:
            raise ValueError("batch_size must be positive")

        if poll_interval <= 0:
            raise ValueError("poll_interval must be positive")

        self.batch_size = batch_size
        self.poll_interval = poll_interval
        self.stop_event = asyncio.Event()

    def request_shutdown(self):
        logger.info("Shutdown requested")
        self.stop_event.set()

    async def process_once(self):
        """
        Create missing jobs and process one batch.

        Each database operation is committed separately.
        """

        async with AsyncSessionLocal() as session:

            try:
                created = await create_missing_jobs(session)
                await session.commit()

                if created:
                    logger.info(
                        "Created %s new resolution jobs",
                        created,
                    )

                stats = await process_resolution_jobs(
                    session=session,
                    batch_size=self.batch_size,
                )

                await session.commit()

                if stats["processed"] > 0:
                    logger.info(
                        "Processed=%s Matched=%s "
                        "Unmatched=%s Skipped=%s "
                        "Retry=%s Failed=%s",
                        stats["processed"],
                        stats["matched"],
                        stats["unmatched"],
                        stats["skipped"],
                        stats["retry"],
                        stats["failed"],
                    )

                return stats

            except Exception:
                await session.rollback()
                logger.exception(
                    "Resolution worker iteration failed"
                )
                raise

    async def run(self):
        logger.info(
            "Continuous worker started | "
            "batch_size=%s | poll_interval=%ss",
            self.batch_size,
            self.poll_interval,
        )

        while not self.stop_event.is_set():

            try:
                stats = await self.process_once()

                # If a full batch was processed, immediately
                # check for more work.
                if stats["processed"] >= self.batch_size:
                    continue

            except Exception:
                logger.warning(
                    "Worker will retry after %.1f seconds",
                    self.poll_interval,
                )

            # Sleep until the next poll or shutdown.
            try:
                await asyncio.wait_for(
                    self.stop_event.wait(),
                    timeout=self.poll_interval,
                )
            except asyncio.TimeoutError:
                pass

        logger.info("Continuous worker stopped")


def main():
    parser = argparse.ArgumentParser(
        description="Continuous resolution job worker"
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Maximum jobs processed per batch",
    )

    parser.add_argument(
        "--poll-interval",
        type=float,
        default=10.0,
        help="Seconds between polling attempts",
    )

    args = parser.parse_args()

    if args.batch_size < 1:
        parser.error("--batch-size must be positive")

    if args.poll_interval <= 0:
        parser.error("--poll-interval must be positive")

    configure_logging()

    async def runner():
        worker = ContinuousResolutionWorker(
            batch_size=args.batch_size,
            poll_interval=args.poll_interval,
        )

        loop = asyncio.get_running_loop()

        # Linux containers support signal handlers.
        # On platforms that do not, Ctrl+C still works.
        try:
            loop.add_signal_handler(
                signal.SIGTERM,
                worker.request_shutdown,
            )
            loop.add_signal_handler(
                signal.SIGINT,
                worker.request_shutdown,
            )
        except NotImplementedError:
            pass

        await worker.run()

    try:
        asyncio.run(runner())
    except KeyboardInterrupt:
        logger.info("Worker interrupted")


if __name__ == "__main__":
    main()