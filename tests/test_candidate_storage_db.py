import uuid

import pytest
from sqlalchemy import select

from ai_pipeline.database.connection import AsyncSessionLocal
from ai_pipeline.database.models import SourceRecord

from ai_pipeline.services.candidate_storage import save_candidate
from ai_pipeline.services.startup_ingestion import StartupCandidate


def make_unique_candidate():
    unique_id = uuid.uuid4().hex

    return StartupCandidate(
        name=f"TestStartup-{unique_id}",
        github_url=f"https://github.com/test-{unique_id}",
        description="Integration test candidate",
        repository_url=f"https://github.com/test-{unique_id}/project",
        website=None,
        verified_company=False,
    )


@pytest.mark.asyncio
async def test_candidate_database_insert_and_duplicate_prevention():
    candidate = make_unique_candidate()

    async with AsyncSessionLocal() as session:
        try:
            inserted = await save_candidate(
                session,
                candidate,
                "startup_candidate",
            )

            assert inserted is True

            await session.flush()

            statement = select(SourceRecord).where(
                SourceRecord.source_url == candidate.github_url
            )

            record = await session.scalar(statement)

            assert record is not None
            assert record.record_type == "startup_candidate"
            assert record.processing_status == "pending_verification"

            duplicate_inserted = await save_candidate(
                session,
                candidate,
                "startup_candidate",
            )

            assert duplicate_inserted is False

        finally:
            await session.rollback()


@pytest.mark.asyncio
async def test_candidate_database_rollback():
    candidate = make_unique_candidate()

    async with AsyncSessionLocal() as session:
        try:
            inserted = await save_candidate(
                session,
                candidate,
                "startup_candidate",
            )

            assert inserted is True

            await session.flush()

            statement = select(SourceRecord).where(
                SourceRecord.source_url == candidate.github_url
            )

            record = await session.scalar(statement)
            assert record is not None

        finally:
            await session.rollback()

    async with AsyncSessionLocal() as session:
        statement = select(SourceRecord).where(
            SourceRecord.source_url == candidate.github_url
        )

        record = await session.scalar(statement)

        assert record is None