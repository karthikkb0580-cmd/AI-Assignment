import asyncio
import os
from dataclasses import dataclass

import httpx
from dotenv import load_dotenv

load_dotenv()


GITHUB_API = "https://api.github.com"


@dataclass
class GitHubRepository:
    repo_id: int
    name: str
    full_name: str
    description: str
    html_url: str
    homepage: str | None
    stars: int
    owner_login: str
    owner_type: str


class GitHubCollector:

    def __init__(self):

        token = os.getenv("GITHUB_TOKEN", "").strip()

        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "AI-Intelligence-Pipeline",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        if token:
            headers["Authorization"] = f"Bearer {token}"

        self.client = httpx.AsyncClient(
            base_url=GITHUB_API,
            headers=headers,
            timeout=30.0,
            follow_redirects=True,
        )

    async def search_repositories(
        self,
        query: str,
        per_page: int = 20,
        page: int = 1,
    ) -> list[GitHubRepository]:

        if not 1 <= per_page <= 100:
            raise ValueError("per_page must be between 1 and 100")

        if page < 1:
            raise ValueError("page must be at least 1")

        response = await self.client.get(
            "/search/repositories",
            params={
                "q": query,
                "sort": "stars",
                "order": "desc",
                "per_page": per_page,
                "page": page,
            },
        )

        response.raise_for_status()

        data = response.json()

        repositories = []

        for item in data.get("items", []):

            owner = item.get("owner") or {}

            repositories.append(
                GitHubRepository(
                    repo_id=item["id"],
                    name=item["name"],
                    full_name=item["full_name"],
                    description=item.get("description") or "",
                    html_url=item["html_url"],
                    homepage=item.get("homepage"),
                    stars=item.get("stargazers_count", 0),
                    owner_login=owner.get("login", ""),
                    owner_type=owner.get("type", ""),
                )
            )

        return repositories

    async def close(self):
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        await self.close()


async def main():

    print("\nConnecting to GitHub API...")

    async with GitHubCollector() as collector:

        repositories = await collector.search_repositories(
            query="topic:artificial-intelligence stars:>100",
            per_page=5,
        )

    print(f"\nRepositories fetched: {len(repositories)}")

    for repo in repositories:

        print("\n" + "=" * 50)

        print(f"Repository: {repo.full_name}")
        print(f"Description: {repo.description}")
        print(f"Stars: {repo.stars}")
        print(f"URL: {repo.html_url}")
        print(f"Owner: {repo.owner_login}")
        print(f"Owner Type: {repo.owner_type}")


if __name__ == "__main__":
    asyncio.run(main())