from ai_pipeline.crawlers.github import GitHubRepository

from ai_pipeline.services.startup_ingestion import (
    extract_startup_candidate,
    extract_unique_startup_candidates,
    normalize_organization_name,
)


def make_repository(
    owner_login="example-ai",
    owner_type="Organization",
    repo_name="example-project",
):
    return GitHubRepository(
        repo_id=123,
        name=repo_name,
        full_name=f"{owner_login}/{repo_name}",
        description="Example AI project",
        html_url=f"https://github.com/{owner_login}/{repo_name}",
        homepage="https://example.com",
        stars=500,
        owner_login=owner_login,
        owner_type=owner_type,
    )


def test_organization_extraction():
    repository = make_repository()

    candidate = extract_startup_candidate(repository)

    assert candidate is not None
    assert candidate.name == "example-ai"
    assert candidate.verified_company is False


def test_personal_account_is_skipped():
    repository = make_repository(owner_type="User")

    candidate = extract_startup_candidate(repository)

    assert candidate is None


def test_organization_name_normalization():
    assert normalize_organization_name(
        "  Example   AI  "
    ) == "example ai"


def test_duplicate_organizations():
    repositories = [
        make_repository(repo_name="project-one"),
        make_repository(repo_name="project-two"),
    ]

    candidates = extract_unique_startup_candidates(
        repositories
    )

    assert len(candidates) == 1


def test_candidate_website():
    repository = make_repository()

    candidate = extract_startup_candidate(repository)

    assert candidate is not None
    assert candidate.website == "https://example.com"