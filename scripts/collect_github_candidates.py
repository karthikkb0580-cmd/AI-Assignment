import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from ai_pipeline.crawlers.github import GitHubCollector

from ai_pipeline.database.connection import AsyncSessionLocal

from ai_pipeline.services.startup_ingestion import (
    extract_unique_startup_candidates,
)

from ai_pipeline.services.product_ingestion import (
    extract_unique_product_candidates,
)

from ai_pipeline.services.candidate_storage import (
    save_candidate,
)


async def save_all_candidates(
    session: AsyncSession,
    startups: list,
    products: list,
):
    startup_inserted = 0
    product_inserted = 0

    for startup in startups:
        inserted = await save_candidate(
            session,
            startup,
            "startup_candidate",
        )

        if inserted:
            startup_inserted += 1

    for product in products:
        inserted = await save_candidate(
            session,
            product,
            "product_candidate",
        )

        if inserted:
            product_inserted += 1

    await session.commit()

    return startup_inserted, product_inserted


async def main():

    print("\nFetching AI repositories from GitHub...")

    async with GitHubCollector() as collector:

        repositories = await collector.search_repositories(
            query="topic:artificial-intelligence stars:>100",
            per_page=30,
        )

    print(f"Repositories fetched: {len(repositories)}")

    startups = extract_unique_startup_candidates(
        repositories
    )

    products = extract_unique_product_candidates(
        repositories
    )

    print(f"Startup candidates extracted: {len(startups)}")
    print(f"Product candidates extracted: {len(products)}")

    async with AsyncSessionLocal() as session:

        startup_count, product_count = await save_all_candidates(
            session,
            startups,
            products,
        )

    print("\nDATABASE INGESTION SUMMARY")
    print("=" * 55)

    print(f"New startup candidates: {startup_count}")
    print(f"New product candidates: {product_count}")

    print("=" * 55)


if __name__ == "__main__":
    asyncio.run(main())