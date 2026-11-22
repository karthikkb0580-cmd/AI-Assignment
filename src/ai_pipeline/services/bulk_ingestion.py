import csv
import hashlib
import json
import logging
import os
import time

from dataclasses import dataclass
from pathlib import Path

import asyncpg


logger = logging.getLogger(__name__)


@dataclass
class IngestionStats:
    total_read: int = 0
    inserted: int = 0
    duplicates: int = 0
    invalid: int = 0
    batches: int = 0
    duration_seconds: float = 0.0


def calculate_hash(value: str) -> str:
    return hashlib.sha256(
        value.strip().lower().encode("utf-8")
    ).hexdigest()


def calculate_file_fingerprint(file_path: Path) -> str:
    """
    Calculate SHA256 without loading the entire file into memory.
    """

    sha256 = hashlib.sha256()

    with file_path.open("rb") as file:
        while True:
            chunk = file.read(1024 * 1024)

            if not chunk:
                break

            sha256.update(chunk)

    return sha256.hexdigest()


class BulkCSVIngestor:

    def __init__(
        self,
        database_url: str,
        batch_size: int = 1000,
        checkpoint_file: str = "checkpoints/bulk_ingestion.json",
    ):
        if batch_size <= 0:
            raise ValueError(
                "batch_size must be greater than zero"
            )

        self.database_url = database_url
        self.batch_size = batch_size
        self.checkpoint_file = Path(checkpoint_file)

    def load_checkpoint(
        self,
        file_fingerprint: str,
    ) -> int:
        """
        Load checkpoint and verify that it belongs
        to the current CSV file.
        """

        if not self.checkpoint_file.exists():
            return 0

        with self.checkpoint_file.open(
            "r",
            encoding="utf-8",
        ) as file:
            checkpoint = json.load(file)

        saved_fingerprint = checkpoint.get(
            "file_fingerprint"
        )

        if saved_fingerprint != file_fingerprint:
            raise ValueError(
                "Checkpoint does not match the current CSV file. "
                "Use a different --checkpoint path for this dataset."
            )

        last_row = int(
            checkpoint.get("last_processed_row", 0)
        )

        if last_row < 0:
            raise ValueError(
                "Invalid checkpoint: negative row number"
            )

        return last_row

    def save_checkpoint(
        self,
        row_number: int,
        file_fingerprint: str,
    ):
        """
        Write checkpoint to a temporary file,
        then atomically replace the previous checkpoint.
        """

        self.checkpoint_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        checkpoint = {
            "version": 2,
            "last_processed_row": row_number,
            "file_fingerprint": file_fingerprint,
        }

        temporary_file = self.checkpoint_file.with_name(
            self.checkpoint_file.name + ".tmp"
        )

        with temporary_file.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                checkpoint,
                file,
                indent=2,
            )

            file.flush()
            os.fsync(file.fileno())

        temporary_file.replace(
            self.checkpoint_file
        )

    async def _create_table(
        self,
        connection,
    ):
        await connection.execute(
            """
            CREATE TABLE IF NOT EXISTS bulk_startup_records (
                id BIGSERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                website TEXT,
                source_url TEXT,
                content_hash TEXT UNIQUE NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
            """
        )

    async def _insert_batch(
        self,
        connection,
        batch,
    ) -> int:
        """
        Insert records using PostgreSQL COPY.

        Duplicate hashes inside the batch and duplicates
        already in PostgreSQL are both ignored.
        """

        if not batch:
            return 0

        async with connection.transaction():

            await connection.execute(
                """
                CREATE TEMP TABLE IF NOT EXISTS
                temp_bulk_startups (
                    name TEXT,
                    website TEXT,
                    source_url TEXT,
                    content_hash TEXT
                ) ON COMMIT DELETE ROWS
                """
            )

            await connection.copy_records_to_table(
                "temp_bulk_startups",
                records=batch,
                columns=[
                    "name",
                    "website",
                    "source_url",
                    "content_hash",
                ],
            )

            inserted = await connection.fetchval(
                """
                WITH inserted AS (
                    INSERT INTO bulk_startup_records (
                        name,
                        website,
                        source_url,
                        content_hash
                    )
                    SELECT
                        name,
                        website,
                        source_url,
                        content_hash
                    FROM (
                        SELECT DISTINCT ON (content_hash)
                            name,
                            website,
                            source_url,
                            content_hash
                        FROM temp_bulk_startups
                        ORDER BY content_hash
                    ) AS deduplicated
                    ON CONFLICT (content_hash)
                    DO NOTHING
                    RETURNING id
                )
                SELECT COUNT(*) FROM inserted
                """
            )

        inserted = int(inserted)

        logger.info(
            "Batch processed: %s records, %s inserted",
            len(batch),
            inserted,
        )

        return inserted

    async def ingest(
        self,
        csv_path: str,
        table_name: str = "bulk_startup_records",
    ) -> IngestionStats:
        """
        Stream a CSV file into PostgreSQL.

        A checkpoint is advanced only after the associated
        database batch commits successfully.

        If the process crashes after commit but before the
        checkpoint is written, replay is safe because the
        destination has a unique content_hash constraint.
        """

        if table_name != "bulk_startup_records":
            raise ValueError(
                "Only bulk_startup_records is supported"
            )

        started_at = time.perf_counter()

        stats = IngestionStats()

        csv_file = Path(csv_path)

        if not csv_file.is_file():
            raise FileNotFoundError(csv_file)

        fingerprint = calculate_file_fingerprint(
            csv_file
        )

        last_processed_row = self.load_checkpoint(
            fingerprint
        )

        logger.info(
            "Resuming ingestion after row %s",
            last_processed_row,
        )

        connection = await asyncpg.connect(
            self.database_url
        )

        try:
            await self._create_table(connection)

            batch = []
            last_seen_row = 0

            with csv_file.open(
                "r",
                encoding="utf-8-sig",
                newline="",
            ) as file:

                reader = csv.DictReader(file)

                if reader.fieldnames is None:
                    logger.warning(
                        "CSV file is empty"
                    )

                    return stats

                required_columns = {
                    "name",
                    "website",
                    "source_url",
                }

                if not required_columns.issubset(
                    set(reader.fieldnames)
                ):
                    raise ValueError(
                        "CSV must contain name, website, "
                        "and source_url columns"
                    )

                for row_number, row in enumerate(
                    reader,
                    start=1,
                ):
                    last_seen_row = row_number

                    if row_number <= last_processed_row:
                        continue

                    stats.total_read += 1

                    name = (
                        row.get("name") or ""
                    ).strip()

                    website = (
                        row.get("website") or ""
                    ).strip()

                    source_url = (
                        row.get("source_url") or ""
                    ).strip()

                    if not name:
                        stats.invalid += 1

                    else:
                        content_hash = calculate_hash(
                            f"{name}|{website}"
                        )

                        batch.append(
                            (
                                name,
                                website,
                                source_url,
                                content_hash,
                            )
                        )

                    # Checkpoint after every batch_size input rows,
                    # including invalid rows.
                    if (
                        stats.total_read % self.batch_size == 0
                    ):
                        inserted = await self._insert_batch(
                            connection,
                            batch,
                        )

                        stats.inserted += inserted

                        stats.duplicates += (
                            len(batch) - inserted
                        )

                        stats.batches += 1

                        self.save_checkpoint(
                            row_number,
                            fingerprint,
                        )

                        batch.clear()

                # Process remaining valid records.
                if batch:
                    inserted = await self._insert_batch(
                        connection,
                        batch,
                    )

                    stats.inserted += inserted

                    stats.duplicates += (
                        len(batch) - inserted
                    )

                    stats.batches += 1

                # Also advances the checkpoint past trailing
                # invalid rows.
                self.save_checkpoint(
                    last_seen_row,
                    fingerprint,
                )

        finally:
            await connection.close()

        stats.duration_seconds = (
            time.perf_counter() - started_at
        )

        return stats