import argparse
import asyncio

from ai_pipeline.database.connection import AsyncSessionLocal
from ai_pipeline.services.resolution_worker import process_extractions


async def run(limit: int):
    async with AsyncSessionLocal() as session:
        try:
            stats = await process_extractions(
                session=session,
                limit=limit,
            )

            await session.commit()

            print("\nENTITY RESOLUTION RESULTS")
            print("-------------------------")
            print(f"Processed: {stats.processed}")
            print(f"Matched:   {stats.resolved}")
            print(f"Unmatched: {stats.unmatched}")
            print(f"Skipped:   {stats.skipped}")
            print(f"Failed:    {stats.failed}")

        except Exception:
            await session.rollback()
            raise


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--limit",
        type=int,
        default=100,
    )

    args = parser.parse_args()

    asyncio.run(run(args.limit))


if __name__ == "__main__":
    main()