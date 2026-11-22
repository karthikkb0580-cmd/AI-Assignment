import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

from ai_pipeline.services.bulk_ingestion import BulkCSVIngestor


def configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Scalable bulk CSV ingestion pipeline"
    )

    parser.add_argument(
        "--file",
        type=str,
        required=True,
        help="Path to the CSV dataset",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Number of records per batch (default: 1000)",
    )

    parser.add_argument(
        "--checkpoint",
        type=str,
        default="checkpoints/bulk_ingestion.json",
        help="Path to the checkpoint file",
    )

    return parser.parse_args()


def get_database_url():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is missing. "
            "Check your .env configuration."
        )

    # Convert SQLAlchemy's async PostgreSQL URL
    # into the format accepted by asyncpg.
    if database_url.startswith("postgresql+asyncpg://"):
        database_url = database_url.replace(
            "postgresql+asyncpg://",
            "postgresql://",
            1,
        )

    return database_url


async def run_ingestion(args):
    csv_path = Path(args.file)

    if not csv_path.is_file():
        raise FileNotFoundError(
            f"CSV file does not exist: {csv_path}"
        )

    if args.batch_size <= 0:
        raise ValueError(
            "Batch size must be greater than zero."
        )

    database_url = get_database_url()

    logging.info("Starting bulk ingestion")
    logging.info("Input file: %s", csv_path)
    logging.info("Batch size: %s", args.batch_size)
    logging.info("Checkpoint: %s", args.checkpoint)

    ingestor = BulkCSVIngestor(
        database_url=database_url,
        batch_size=args.batch_size,
        checkpoint_file=args.checkpoint,
    )

    stats = await ingestor.ingest(
        csv_path=str(csv_path),
    )

    print()
    print("=" * 50)
    print("BULK INGESTION SUMMARY")
    print("=" * 50)

    print(f"Records read       : {stats.total_read}")
    print(f"Records inserted   : {stats.inserted}")
    print(f"Duplicate records  : {stats.duplicates}")
    print(f"Invalid records    : {stats.invalid}")
    print(f"Batches processed  : {stats.batches}")
    print(f"Duration           : {stats.duration_seconds:.2f} seconds")

    if stats.duration_seconds > 0:
        throughput = (
            stats.total_read / stats.duration_seconds
        )

        print(
            f"Throughput         : {throughput:.2f} records/second"
        )

    print("=" * 50)
    print("Bulk ingestion completed successfully.")
    print("=" * 50)


def main():
    configure_logging()

    args = parse_arguments()

    try:
        asyncio.run(run_ingestion(args))

    except KeyboardInterrupt:
        logging.warning(
            "Bulk ingestion interrupted by user."
        )
        sys.exit(130)

    except FileNotFoundError as error:
        logging.error("File error: %s", error)
        sys.exit(1)

    except ValueError as error:
        logging.error("Configuration error: %s", error)
        sys.exit(1)

    except Exception:
        logging.exception(
            "Bulk ingestion failed"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()