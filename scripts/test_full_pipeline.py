import asyncio
import hashlib
import uuid

from sqlalchemy import func, select

from ai_pipeline.database.connection import AsyncSessionLocal
from ai_pipeline.database.models import (
    SourceRecord,
    ExtractionRecord,
    ResolutionJob,
    EntityMapping,
)
from ai_pipeline.services.extraction_storage import (
    save_extraction_success,
)
from ai_pipeline.services.resolution_jobs import (
    create_missing_jobs,
    process_resolution_jobs,
)
from ai_pipeline.services.normalization import normalize_name


async def main():
    unique_id = uuid.uuid4().hex

    startup_name = f"Pipeline Integration Test {unique_id[:12]}"
    source_url = f"https://example.invalid/pipeline/{unique_id}"

    raw_content = (
        f"Startup Name: {startup_name}\n"
        "Website: Not available"
    )

    content_hash = hashlib.sha256(
        raw_content.encode("utf-8")
    ).hexdigest()

    print("\nSTEP 15.8 - FULL PIPELINE INTEGRATION TEST")
    print("=" * 55)

    print(f"Startup: {startup_name}")
    print(f"Source: {source_url}")

    async with AsyncSessionLocal() as session:
        try:
            # -----------------------------------------
            # 1. Create synthetic source record
            # -----------------------------------------

            source = SourceRecord(
                source_name="integration_test",
                source_url=source_url,
                record_type="startup",
                raw_content=raw_content,
                raw_metadata={
                    "test": True,
                    "synthetic": True,
                },
                content_hash=content_hash,
                processing_status="PENDING",
            )

            session.add(source)
            await session.flush()

            print("\nPASS: Source record created")

            # -----------------------------------------
            # 2. Save a controlled extraction result
            # -----------------------------------------

            extracted_data = {
                "results": [
                    {
                        "entity_type": "startup",
                        "startup": {
                            "name": startup_name,
                            "website": None,
                        },
                        "evidence": [
                            {
                                "field": "name",
                                "quote": startup_name,
                                "source_url": source_url,
                            }
                        ],
                        "needs_review": True,
                    }
                ],
                "needs_review": True,
                "mock": False,
                "synthetic_test": True,
            }

            extraction = await save_extraction_success(
                session=session,
                source_record_id=source.id,
                content_hash=content_hash,
                extracted_data=extracted_data,
                extractor_version="llm-v1",
            )

            await session.flush()

            assert extraction.status == "completed"

            print("PASS: Extraction result saved")

            # -----------------------------------------
            # 3. Create resolution jobs
            # -----------------------------------------

            created = await create_missing_jobs(session)

            await session.flush()

            print(f"Resolution jobs created: {created}")

            job_query = select(ResolutionJob).where(
                ResolutionJob.extraction_id == extraction.id
            )

            job = (
                await session.execute(job_query)
            ).scalar_one_or_none()

            assert job is not None, (
                "Resolution job was not created"
            )

            print("PASS: Resolution job created")

            # -----------------------------------------
            # 4. Process resolution jobs
            # -----------------------------------------

            stats = await process_resolution_jobs(
                session=session,
                batch_size=100,
            )

            await session.flush()

            print(f"Resolution stats: {stats}")

            await session.refresh(job)

            assert job.status == "completed", (
                f"Unexpected job status: {job.status}"
            )

            print("PASS: Resolution job completed")

            # -----------------------------------------
            # 5. Verify entity mapping
            # -----------------------------------------

            normalized = normalize_name(startup_name)

            mapping_query = select(EntityMapping).where(
                EntityMapping.normalized_name == normalized,
                EntityMapping.source_url == source_url,
            )

            mapping = (
                await session.execute(mapping_query)
            ).scalar_one_or_none()

            assert mapping is not None, (
                "Entity mapping was not created"
            )

            print("PASS: Entity mapping created")

            # -----------------------------------------
            # 6. Verify duplicate prevention
            # -----------------------------------------

            from ai_pipeline.services.entity_resolution import (
                resolve_startup,
            )

            await resolve_startup(
                session=session,
                name=startup_name,
                source_url=source_url,
            )

            await session.flush()

            count_query = select(func.count()).select_from(
                EntityMapping
            ).where(
                EntityMapping.normalized_name == normalized,
                EntityMapping.source_url == source_url,
            )

            count = (
                await session.execute(count_query)
            ).scalar_one()

            assert count == 1, (
                f"Expected 1 mapping, found {count}"
            )

            print("PASS: Duplicate mapping prevented")

            # -----------------------------------------
            # 7. Roll back synthetic test data
            # -----------------------------------------

            await session.rollback()

            print("PASS: Test transaction rolled back")
            print("\nALL FULL PIPELINE TESTS PASSED")

        except Exception:
            await session.rollback()

            print("\nFULL PIPELINE TEST FAILED")
            raise


if __name__ == "__main__":
    asyncio.run(main())