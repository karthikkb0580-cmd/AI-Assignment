import asyncio

from sqlalchemy import select

from ai_pipeline.database.connection import AsyncSessionLocal
from ai_pipeline.database.models import Startup
from ai_pipeline.database.repositories import create_startup


TEST_NAME = "Stage 2 Demo Startup"
NORMALIZED_NAME = "stage 2 demo startup"


async def main():

    async with AsyncSessionLocal() as session:

        # Remove any leftover synthetic record from an earlier test.
        result = await session.execute(
            select(Startup).where(
                Startup.normalized_name == NORMALIZED_NAME
            )
        )

        existing = result.scalar_one_or_none()

        if existing is not None:
            await session.delete(existing)
            await session.commit()

        print("\nTesting duplicate prevention...\n")

        startup1 = await create_startup(
            session,
            name=TEST_NAME,
            source_url="https://example.com/stage-2-demo",
            description="Synthetic database test record",
        )

        startup2 = await create_startup(
            session,
            name="  Stage 2 Demo Startup  ",
            source_url="https://example.com/stage-2-demo",
            description="Synthetic database test record",
        )

        print("First startup ID:", startup1.id)
        print("Second startup ID:", startup2.id)

        assert startup1.id == startup2.id, (
            "Duplicate prevention failed"
        )

        print("\nPASS: Duplicate startup was prevented")


if __name__ == "__main__":
    asyncio.run(main())