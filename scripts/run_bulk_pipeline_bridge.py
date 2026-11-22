import argparse
import asyncio
import logging
import os
import sys

from ai_pipeline.services.bulk_pipeline_bridge import (
    transfer_bulk_records,
)


def get_database_url():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is missing from the environment"
        )

    if database_url.startswith("postgresql+asyncpg://"):
        database_url = database_url.replace(
            "postgresql+asyncpg://",
            "postgresql://",
            1,
        )

    return database_url


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Transfer bulk startup records into the AI pipeline"
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of records to transfer",
    )

    parser.add_argument(
        "--after-id",
        type=int,
        default=0,
        help="Only transfer staging records with ID greater than this value",
    )

    return parser.parse_args()


async def main():
    args = parse_arguments()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    stats = await transfer_bulk_records(
        database_url=get_database_url(),
        batch_size=args.batch_size,
        after_id=args.after_id,
    )

    print()
    print("=" * 50)
    print("BULK PIPELINE BRIDGE SUMMARY")
    print("=" * 50)

    print(f"Records fetched     : {stats.fetched}")
    print(f"Records inserted    : {stats.inserted}")
    print(f"Duplicates skipped  : {stats.duplicates}")

    print("=" * 50)


if __name__ == "__main__":
    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        print("Bridge interrupted")
        sys.exit(130)

    except Exception:
        logging.exception("Bridge execution failed")
        sys.exit(1)