from dataclasses import dataclass
from urllib.parse import urlparse

from ai_pipeline.crawlers.github import GitHubRepository


@dataclass
class StartupCandidate:
    name: str
    github_url: str
    description: str
    repository_url: str
    website: str | None
    verified_company: bool = False


def normalize_organization_name(name: str) -> str:
    """Normalize organization names for comparison."""
    return " ".join(name.casefold().strip().split())


def is_valid_website(url: str | None) -> bool:
    """Check whether a website has a valid HTTP(S) URL structure."""

    if not url:
        return False

    parsed = urlparse(url)

    return (
        parsed.scheme in {"http", "https"}
        and bool(parsed.hostname)
    )


def extract_startup_candidate(
    repository: GitHubRepository,
) -> StartupCandidate | None:
    """
    Extract a potential company from a GitHub repository.

    A GitHub organization is only a candidate.
    It is NOT automatically a verified startup.
    """

    if repository.owner_type != "Organization":
        return None

    if not repository.owner_login:
        return None

    name = repository.owner_login.strip()

    if not name:
        return None

    website = (
        repository.homepage
        if is_valid_website(repository.homepage)
        else None
    )

    return StartupCandidate(
        name=name,
        github_url=f"https://github.com/{name}",
        description=repository.description.strip(),
        repository_url=repository.html_url,
        website=website,
        verified_company=False,
    )


def extract_unique_startup_candidates(
    repositories: list[GitHubRepository],
) -> list[StartupCandidate]:
    """Extract and deduplicate GitHub organization candidates."""

    candidates = []
    seen_organizations = set()

    for repository in repositories:
        candidate = extract_startup_candidate(repository)

        if candidate is None:
            continue

        normalized_name = normalize_organization_name(
            candidate.name
        )

        if normalized_name in seen_organizations:
            continue

        seen_organizations.add(normalized_name)

        candidates.append(candidate)

    return candidates