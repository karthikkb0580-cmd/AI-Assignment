import asyncio

from sqlalchemy import func, select

from ai_pipeline.database.connection import AsyncSessionLocal
from ai_pipeline.database.models import (
    SourceRecord,
    ExtractionRecord,
    ResolutionJob,
    EntityMapping,
    Startup,
)


async def count_rows(session, model):
    result = await session.execute(
        select(func.count()).select_from(model)
    )
    return result.scalar_one()


async def grouped_status(session, model, status_column):
    result = await session.execute(
        select(
            status_column,
            func.count(),
        ).select_from(model).group_by(status_column)
    )

    return result.all()


async def main():
    async with AsyncSessionLocal() as session:
        print("\nAI INTELLIGENCE PIPELINE METRICS")
        print("=" * 50)

        models = [
            ("Source records", SourceRecord),
            ("Extractions", ExtractionRecord),
            ("Resolution jobs", ResolutionJob),
            ("Entity mappings", EntityMapping),
            ("Startups", Startup),
        ]

        for label, model in models:
            count = await count_rows(session, model)
            print(f"{label}: {count}")

        print("\nEXTRACTION STATUS")

        extraction_status = await grouped_status(
            session,
            ExtractionRecord,
            ExtractionRecord.status,
        )

        for status, count in extraction_status:
            print(f"{status}: {count}")

        print("\nRESOLUTION STATUS")

        resolution_status = await grouped_status(
            session,
            ResolutionJob,
            ResolutionJob.status,
        )

        for status, count in resolution_status:
            print(f"{status}: {count}")

        print("\nMetrics collected successfully.")


if __name__ == "__main__":
    asyncio.run(main())
