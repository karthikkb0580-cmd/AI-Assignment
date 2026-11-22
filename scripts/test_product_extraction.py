import asyncio

from ai_pipeline.crawlers.github import GitHubCollector

from ai_pipeline.services.product_ingestion import (
    extract_unique_product_candidates,
)


async def main():

    print("\nFetching AI repositories from GitHub...")

    async with GitHubCollector() as collector:

        repositories = await collector.search_repositories(
            query="topic:artificial-intelligence stars:>100",
            per_page=20,
        )

    print(f"\nRepositories fetched: {len(repositories)}")

    products = extract_unique_product_candidates(
        repositories
    )

    print("\nAI PRODUCT CANDIDATES")
    print("=" * 60)

    for index, product in enumerate(products, start=1):

        print(f"\nProduct Candidate {index}")

        print(f"Name: {product.name}")

        print(f"Description: {product.description}")

        print(f"Repository: {product.repository_url}")

        print(
            f"Homepage: {product.homepage or 'Not available'}"
        )

        print(f"Stars: {product.stars}")

        print(f"Owner: {product.owner_login}")

        print(f"Verified: {product.verified_product}")

    print("\nCOLLECTION SUMMARY")
    print("=" * 60)

    print(f"Repositories fetched: {len(repositories)}")

    print(f"Product candidates: {len(products)}")

    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())