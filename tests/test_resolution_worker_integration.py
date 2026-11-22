import os
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from ai_pipeline.database.models import (
    Base,
    Startup,
    SourceRecord,
    ExtractionRecord,
    EntityMapping,
)
from ai_pipeline.services.resolution_worker import process_extractions


@pytest.mark.asyncio
async def test_complete_resolution_pipeline():
    database_url = os.getenv("TEST_DATABASE_URL")

    if not database_url:
        pytest.skip("TEST_DATABASE_URL not configured")

    if not database_url.endswith("/ai_intelligence_test"):
        raise RuntimeError("Refusing to use a non-test database")

    engine = create_async_engine(database_url)

    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        async with engine.connect() as connection:
            transaction = await connection.begin()

            try:
                async with AsyncSession(
                    bind=connection,
                    expire_on_commit=False,
                    join_transaction_mode="create_savepoint",
                ) as session:

                    unique_id = uuid.uuid4().hex[:8]

                    startup_name = f"NeuralForge {unique_id}"
                    source_url = f"https://example.com/{unique_id}"

                    startup = Startup(
                        id=uuid.uuid4(),
                        name=startup_name,
                        normalized_name=startup_name.casefold(),
                        source_url=source_url,
                    )

                    session.add(startup)
                    await session.flush()

                    source = SourceRecord(
                        id=uuid.uuid4(),
                        source_name="integration-test",
                        source_url=source_url,
                        record_type="startup",
                        raw_content=f"{startup_name} is an AI startup.",
                        content_hash=uuid.uuid4().hex,
                        processing_status="completed",
                    )

                    session.add(source)
                    await session.flush()

                    extraction = ExtractionRecord(
                        id=uuid.uuid4(),
                        source_record_id=source.id,
                        content_hash=source.content_hash,
                        extractor_version="integration-test",
                        status="completed",
                        extracted_data={
                            "entity_type": "startup",
                            "startup": {
                                "name": startup_name,
                            },
                            "needs_review": True,
                        },
                    )

                    session.add(extraction)
                    await session.flush()

                    stats = await process_extractions(
                        session=session,
                        limit=100,
                    )

                    await session.flush()

                    assert stats.resolved >= 1
                    assert stats.failed == 0

                    result = await session.scalars(
                        select(EntityMapping).where(
                            EntityMapping.startup_id == startup.id
                        )
                    )

                    mappings = result.all()

                    assert len(mappings) == 1

            finally:
                await transaction.rollback()

    finally:
        await engine.dispose()