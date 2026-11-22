import asyncio

from ai_pipeline.crawlers.github import GitHubCollector

from ai_pipeline.services.startup_ingestion import (
    extract_unique_startup_candidates,
)


async def main():

    print("\nFetching AI repositories from GitHub...")

    async with GitHubCollector() as collector:

        repositories = await collector.search_repositories(
            query="topic:artificial-intelligence stars:>100",
            per_page=20,
        )

    print(f"\nRepositories fetched: {len(repositories)}")

    candidates = extract_unique_startup_candidates(
        repositories
    )

    print("\nSTARTUP CANDIDATES")
    print("=" * 60)

    for index, startup in enumerate(candidates, start=1):

        print(f"\nCandidate {index}")

        print(f"Name: {startup.name}")
        print(f"GitHub: {startup.github_url}")
        print(f"Website: {startup.website or 'Not available'}")
        print(f"Repository: {startup.repository_url}")
        print(f"Verified: {startup.verified_company}")

    print("\nCOLLECTION SUMMARY")
    print("=" * 60)
    print(f"Repositories fetched: {len(repositories)}")
    print(f"Unique startup candidates: {len(candidates)}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())