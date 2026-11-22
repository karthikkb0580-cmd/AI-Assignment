import asyncio
import uuid

from sqlalchemy import select, func

from ai_pipeline.database.connection import AsyncSessionLocal
from ai_pipeline.database.models import EntityMapping
from ai_pipeline.services.entity_resolution import resolve_startup
from ai_pipeline.services.normalization import normalize_name


async def main():

    test_name = f"Pipeline Test Startup {uuid.uuid4().hex[:12]}"
    test_source = f"https://example.invalid/test/{uuid.uuid4()}"

    normalized = normalize_name(test_name)

    print("\nSTEP 15.7 - DATABASE RESOLUTION TEST")
    print("-----------------------------------")
    print(f"Test startup: {test_name}")
    print(f"Source: {test_source}")

    async with AsyncSessionLocal() as session:

        try:

            # -------------------------------------------------
            # 1. Count mappings before resolution
            # -------------------------------------------------

            before_query = select(func.count()).select_from(
                EntityMapping
            ).where(
                EntityMapping.normalized_name == normalized,
                EntityMapping.source_url == test_source,
            )

            before = (
                await session.execute(before_query)
            ).scalar_one()

            print(f"\nMappings before: {before}")

            # -------------------------------------------------
            # 2. Resolve the startup
            # -------------------------------------------------

            result1 = await resolve_startup(
                session=session,
                name=test_name,
                source_url=test_source,
            )

            await session.flush()

            print("\nFirst resolution:")
            print(f"Matched: {result1.matched}")
            print(f"Canonical name: {result1.canonical_name}")
            print(f"Match method: {result1.match_method}")
            print(f"Confidence: {result1.confidence_score}")
            print(f"Needs review: {result1.needs_review}")

            # -------------------------------------------------
            # 3. Resolve the same startup again
            # -------------------------------------------------

            result2 = await resolve_startup(
                session=session,
                name=test_name,
                source_url=test_source,
            )

            await session.flush()

            # -------------------------------------------------
            # 4. Count mappings after resolution
            # -------------------------------------------------

            after_query = select(func.count()).select_from(
                EntityMapping
            ).where(
                EntityMapping.normalized_name == normalized,
                EntityMapping.source_url == test_source,
            )

            after = (
                await session.execute(after_query)
            ).scalar_one()

            print(f"\nMappings after two resolutions: {after}")

            # -------------------------------------------------
            # 5. Assertions
            # -------------------------------------------------

            assert before == 0
            assert after == 1, "Duplicate mapping was created"
            assert result1.needs_review is True
            assert result2.needs_review is True

            print("\nPASS: Entity mapping created")
            print("PASS: Duplicate mapping prevented")
            print("PASS: Human review required")

            # -------------------------------------------------
            # 6. Roll back test data
            # -------------------------------------------------

            await session.rollback()

            print("PASS: Test transaction rolled back")
            print("\nALL DATABASE RESOLUTION TESTS PASSED")

        except Exception:

            await session.rollback()

            print("\nDATABASE RESOLUTION TEST FAILED")

            raise


if __name__ == "__main__":
    asyncio.run(main())