
import argparse
import asyncio

from ai_pipeline.database.connection import AsyncSessionLocal
from ai_pipeline.services.resolution_jobs import create_missing_jobs, process_resolution_jobs


async def run(batch_size: int) -> None:
    totals = {key: 0 for key in ("processed", "matched", "unmatched", "skipped", "retry", "failed")}

    async with AsyncSessionLocal() as session:
        try:
            created = await create_missing_jobs(session)
            await session.commit()
            print(f"Resolution jobs created: {created}")

            while True:
                stats = await process_resolution_jobs(session, batch_size=batch_size)
                await session.commit()
                if not stats["processed"]:
                    break
                for key in totals:
                    totals[key] += stats[key]
                print("Batch: " + ", ".join(f"{value} {key}" for key, value in stats.items()))
        except Exception:
            await session.rollback()
            raise

    print("\nRESOLUTION JOB SUMMARY")
    for key, value in totals.items():
        print(f"{key.capitalize()}: {value}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=100)
    args = parser.parse_args()
    if args.batch_size < 1:
        parser.error("--batch-size must be positive")
    asyncio.run(run(args.batch_size))


if __name__ == "__main__":
    main()