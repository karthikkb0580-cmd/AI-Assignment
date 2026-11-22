import argparse
import asyncio
import json
import logging
import os

from sqlalchemy import exists, or_, select

from ai_pipeline.database.connection import AsyncSessionLocal
from ai_pipeline.database.models import SourceRecord, ExtractionRecord

from ai_pipeline.llm.client import ResilientLLMClient
from ai_pipeline.llm.extractor import StructuredExtractor

from ai_pipeline.services.extraction_storage import (
    get_extraction_record,
    save_extraction_success,
    save_extraction_failure,
)
from ai_pipeline.services.data_quality import validate_extraction

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


async def run_extraction(
    limit: int = 5,
    mock: bool = False,
    max_attempts: int = 3,
    source_name: str | None = None,
):
    if limit < 1:
        raise ValueError("limit must be greater than zero")

    if max_attempts < 1:
        raise ValueError("max_attempts must be greater than zero")

    extractor_version = "mock-v1" if mock else "llm-v1"

    logger.info(
        "Starting extraction | mode=%s | version=%s | limit=%s | source=%s",
        "MOCK" if mock else "REAL",
        extractor_version,
        limit,
        source_name or "ALL",
    )

    extractor = None

    if not mock:
        config = {
            "LLM_API_KEY": os.getenv("LLM_API_KEY"),
            "LLM_BASE_URL": os.getenv("LLM_BASE_URL"),
            "LLM_MODEL": os.getenv("LLM_MODEL"),
        }

        missing = [
            key for key, value in config.items()
            if not value
        ]

        if missing:
            raise RuntimeError(
                "Missing LLM configuration: " + ", ".join(missing)
            )

        client = ResilientLLMClient(
            api_key=config["LLM_API_KEY"],
            base_url=config["LLM_BASE_URL"],
            model=config["LLM_MODEL"],
        )

        extractor = StructuredExtractor(client)

    processed = 0
    skipped = 0
    failed = 0

    async with AsyncSessionLocal() as session:
        statement = select(
            SourceRecord.id,
            SourceRecord.content_hash,
            SourceRecord.source_url,
            SourceRecord.raw_content,
            SourceRecord.raw_metadata,
        )

        if source_name:
            statement = statement.where(
                SourceRecord.source_name == source_name
            )

        existing_extraction = (
            select(ExtractionRecord.id)
            .where(
                ExtractionRecord.source_record_id == SourceRecord.id,
                ExtractionRecord.content_hash == SourceRecord.content_hash,
                ExtractionRecord.extractor_version == extractor_version,
            )
            .correlate(SourceRecord)
        )

        statement = statement.where(
            ~exists(
                existing_extraction.where(
                    or_(
                        ExtractionRecord.status == "completed",
                        ExtractionRecord.attempt_count >= max_attempts,
                    )
                )
            )
        )

        statement = statement.order_by(SourceRecord.id).limit(limit)

        result = await session.execute(statement)

        records = [
            {
                "id": row.id,
                "content_hash": row.content_hash,
                "source_url": row.source_url,
                "raw_content": row.raw_content,
                "raw_metadata": row.raw_metadata,
            }
            for row in result.all()
        ]

        logger.info("Found %s matching source records", len(records))

        for record in records:
            record_id = record["id"]
            content_hash = record["content_hash"]
            source_url = record["source_url"]

            try:
                existing = await get_extraction_record(
                    session=session,
                    source_record_id=record_id,
                    content_hash=content_hash,
                    extractor_version=extractor_version,
                )

                if existing and existing.status == "completed":
                    skipped += 1
                    logger.info(
                        "Skipping completed record: %s",
                        record_id,
                    )
                    continue

                if (
                    existing
                    and (existing.attempt_count or 0) >= max_attempts
                ):
                    skipped += 1
                    logger.warning(
                        "Maximum attempts reached: %s",
                        record_id,
                    )
                    continue

                source_text = record["raw_content"]

                if not source_text:
                    source_text = json.dumps(
                        record["raw_metadata"] or {},
                        ensure_ascii=False,
                        default=str,
                    )

                if mock:
                    extracted_data = {
                        "results": [],
                        "needs_review": True,
                        "mock": True,
                        "source_record_id": str(record_id),
                    }
                else:
                    extracted = await extractor.extract(
                        text=source_text,
                        source_url=source_url,
                    )

                    extracted_data = {
                        "results": [
                            item.model_dump(mode="json")
                            for item in extracted
                        ],
                        "needs_review": True,
                        "mock": False,
                    }

                    quality = validate_extraction(
                        data=extracted_data,
                        source_text=source_text,
                    )

                    if not quality.valid:
                        raise ValueError(
                            "Data quality validation failed: "
                            f"{quality.reason}"
                        )

                    logger.info(
                        "Data quality validation passed for record: %s",
                        record_id,
                    )

                await save_extraction_success(
                    session=session,
                    source_record_id=record_id,
                    content_hash=content_hash,
                    extracted_data=extracted_data,
                    extractor_version=extractor_version,
                )

                await session.commit()
                processed += 1

                logger.info(
                    "Successfully processed record: %s",
                    record_id,
                )

            except Exception as exc:
                await session.rollback()
                failed += 1

                logger.exception(
                    "Extraction failed for record: %s",
                    record_id,
                )

                try:
                    await save_extraction_failure(
                        session=session,
                        source_record_id=record_id,
                        content_hash=content_hash,
                        error_message=(
                            f"{type(exc).__name__}: {str(exc)[:500]}"
                        ),
                        extractor_version=extractor_version,
                    )

                    await session.commit()

                except Exception:
                    await session.rollback()

                    logger.exception(
                        "Failed to store extraction error: %s",
                        record_id,
                    )

    logger.info("=" * 50)
    logger.info("EXTRACTION SUMMARY")
    logger.info("Successfully processed: %s", processed)
    logger.info("Skipped: %s", skipped)
    logger.info("Failed: %s", failed)
    logger.info("=" * 50)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="AI Intelligence Pipeline Extraction Worker"
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=5,
    )

    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run without calling an LLM",
    )

    parser.add_argument(
        "--max-attempts",
        type=int,
        default=3,
    )

    parser.add_argument(
        "--source-name",
        type=str,
        default=None,
        help="Only process records from this source",
    )

    args = parser.parse_args()

    asyncio.run(
        run_extraction(
            limit=args.limit,
            mock=args.mock,
            max_attempts=args.max_attempts,
            source_name=args.source_name,
        )
    )