import asyncio
import time

from sqlalchemy import text

from ai_pipeline.database.connection import AsyncSessionLocal


async def main():

    print("=" * 60)
    print("AI INTELLIGENCE PIPELINE")
    print("DATABASE PERFORMANCE REPORT")
    print("=" * 60)

    async with AsyncSessionLocal() as session:

        start = time.perf_counter()

        result = await session.execute(
            text("SELECT 1")
        )

        result.scalar_one()

        elapsed = time.perf_counter() - start

        print(
            f"\nDatabase query latency: "
            f"{elapsed * 1000:.2f} ms"
        )

        tables = [
            "source_records",
            "extraction_results",
            "resolution_jobs",
            "entity_mappings",
            "startups",
            "bulk_startup_records",
        ]

        print("\nDATABASE RECORD COUNTS")
        print("-" * 60)

        for table in tables:

            start = time.perf_counter()

            result = await session.execute(
                text(f"SELECT COUNT(*) FROM {table}")
            )

            count = result.scalar_one()

            elapsed = time.perf_counter() - start

            print(
                f"{table:25} "
                f"{count:10} records "
                f"{elapsed * 1000:10.2f} ms"
            )

        print("\nEXTRACTION STATUS")
        print("-" * 60)

        result = await session.execute(
            text(
                """
                SELECT
                    extractor_version,
                    status,
                    COUNT(*)
                FROM extraction_results
                GROUP BY extractor_version, status
                ORDER BY extractor_version, status
                """
            )
        )

        for version, status, count in result.all():

            print(
                f"{version:15} "
                f"{status:15} "
                f"{count}"
            )

        print("\nRESOLUTION STATUS")
        print("-" * 60)

        result = await session.execute(
            text(
                """
                SELECT status, COUNT(*)
                FROM resolution_jobs
                GROUP BY status
                ORDER BY status
                """
            )
        )

        for status, count in result.all():

            print(
                f"{status:20} {count}"
            )

    print("\nDatabase report completed.")


if __name__ == "__main__":
    asyncio.run(main())