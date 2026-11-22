import asyncio

from sqlalchemy import select

from ai_pipeline.database.connection import AsyncSessionLocal
from ai_pipeline.database.models import (
    ExtractionRecord,
    SourceRecord,
)

from ai_pipeline.services.data_quality import (
    validate_extraction,
)


async def main():

    total = 0
    passed = 0
    failed = 0
    mock = 0

    async with AsyncSessionLocal() as session:

        statement = (
            select(
                ExtractionRecord,
                SourceRecord.raw_content,
            )
            .join(
                SourceRecord,
                ExtractionRecord.source_record_id
                == SourceRecord.id,
            )
            .where(
                ExtractionRecord.status == "completed"
            )
        )

        rows = (
            await session.execute(statement)
        ).all()

        for extraction, source_text in rows:

            total += 1

            data = extraction.extracted_data

            if (
                isinstance(data, dict)
                and data.get("mock") is True
            ):
                mock += 1
                continue

            quality = validate_extraction(
                data=data,
                source_text=source_text or "",
            )

            if quality.valid:
                passed += 1
            else:
                failed += 1

                print(
                    f"INVALID: {extraction.id} "
                    f"| {quality.reason}"
                )

    print("\nEXTRACTION QUALITY AUDIT")
    print("=" * 50)
    print(f"Total completed: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Mock excluded: {mock}")


if __name__ == "__main__":
    asyncio.run(main())