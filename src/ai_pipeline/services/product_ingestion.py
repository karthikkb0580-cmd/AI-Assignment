from dataclasses import dataclass
from urllib.parse import urlparse

from ai_pipeline.crawlers.github import GitHubRepository


@dataclass
class ProductCandidate:
    name: str
    normalized_name: str
    description: str
    repository_url: str
    homepage: str | None
    stars: int
    owner_login: str
    source: str = "github"
    verified_product: bool = False


def normalize_product_name(name: str) -> str:
    """
    Normalize product names for comparison.
    """

    return " ".join(name.casefold().strip().split())


def is_valid_url(url: str | None) -> bool:
    """
    Validate HTTP and HTTPS URLs.
    """

    if not url:
        return False

    parsed = urlparse(url)

    return (
        parsed.scheme in {"http", "https"}
        and bool(parsed.hostname)
    )


def extract_product_candidate(
    repository: GitHubRepository,
) -> ProductCandidate | None:
    """
    Extract an AI product candidate from a GitHub repository.
    """

    if not repository.name.strip():
        return None

    if not is_valid_url(repository.html_url):
        return None

    if not repository.description.strip():
        return None

    homepage = (
        repository.homepage
        if is_valid_url(repository.homepage)
        else None
    )

    return ProductCandidate(
        name=repository.name.strip(),
        normalized_name=normalize_product_name(
            repository.name
        ),
        description=repository.description.strip(),
        repository_url=repository.html_url,
        homepage=homepage,
        stars=max(repository.stars, 0),
        owner_login=repository.owner_login,
        verified_product=False,
    )


def extract_unique_product_candidates(
    repositories: list[GitHubRepository],
) -> list[ProductCandidate]:
    """
    Extract products and remove duplicate repositories.
    """

    candidates = []

    seen_repositories = set()

    for repository in repositories:

        candidate = extract_product_candidate(repository)

        if candidate is None:
            continue

        normalized_url = (
            candidate.repository_url
            .strip()
            .rstrip("/")
            .casefold()
        )

        if normalized_url in seen_repositories:
            continue

        seen_repositories.add(normalized_url)

        candidates.append(candidate)

    return candidates