import json
import logging
import uuid

from dataclasses import dataclass

import asyncpg


logger = logging.getLogger(__name__)


@dataclass
class BridgeStats:
    fetched: int = 0
    inserted: int = 0
    duplicates: int = 0


def build_raw_content(name: str, website: str | None) -> str:
    """Create text suitable for the extraction pipeline."""

    return (
        f"Startup Name: {name}\n"
        f"Website: {website or 'Not available'}"
    )


def build_metadata(
    bulk_id: int,
    name: str,
    website: str | None,
) -> dict:
    """Preserve provenance from the staging table."""

    return {
        "bulk_record_id": bulk_id,
        "name": name,
        "website": website,
        "origin": "bulk_csv_ingestion",
        "verified_company": False,
    }


async def transfer_bulk_records(
    database_url: str,
    batch_size: int = 10,
    after_id: int = 0,
) -> BridgeStats:
    """
    Transfer a page of staged records into source_records.

    after_id is the exclusive lower bound on staging IDs.
    Use the last processed ID to continue with another page.

    The operation is idempotent for records having the same
    source_url and content_hash.
    """

    if batch_size <= 0:
        raise ValueError("batch_size must be greater than zero")

    if after_id < 0:
        raise ValueError("after_id cannot be negative")

    stats = BridgeStats()

    connection = await asyncpg.connect(database_url)

    try:
        records = await connection.fetch(
            """
            SELECT
                id,
                name,
                website,
                source_url,
                content_hash
            FROM bulk_startup_records
            WHERE id > $1
            ORDER BY id
            LIMIT $2
            """,
            after_id,
            batch_size,
        )

        stats.fetched = len(records)

        if not records:
            logger.info("No staging records found")
            return stats

        async with connection.transaction():

            for record in records:

                source_url = (
                    record["source_url"]
                    or record["website"]
                    or f"bulk://startup/{record['id']}"
                )

                raw_content = build_raw_content(
                    name=record["name"],
                    website=record["website"],
                )

                metadata = build_metadata(
                    bulk_id=record["id"],
                    name=record["name"],
                    website=record["website"],
                )

                inserted_id = await connection.fetchval(
                    """
                    INSERT INTO source_records (
                        id,
                        source_name,
                        source_url,
                        record_type,
                        raw_content,
                        raw_metadata,
                        content_hash,
                        processing_status,
                        collected_at
                    )
                    VALUES (
                        $1,
                        $2,
                        $3,
                        $4,
                        $5,
                        $6::json,
                        $7,
                        $8,
                        NOW()
                    )
                    ON CONFLICT (
                        source_url,
                        content_hash
                    )
                    DO NOTHING
                    RETURNING id
                    """,
                    uuid.uuid4(),
                    "bulk_csv",
                    source_url,
                    "startup",
                    raw_content,
                    json.dumps(metadata),
                    record["content_hash"],
                    "PENDING",
                )

                if inserted_id is None:
                    stats.duplicates += 1
                else:
                    stats.inserted += 1

        logger.info(
            "Bridge complete: fetched=%s inserted=%s duplicates=%s",
            stats.fetched,
            stats.inserted,
            stats.duplicates,
        )

        return stats

    finally:
        await connection.close()