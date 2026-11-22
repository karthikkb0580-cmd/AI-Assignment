from ai_pipeline.crawlers.github import GitHubRepository

from ai_pipeline.services.product_ingestion import (
    extract_product_candidate,
    extract_unique_product_candidates,
    normalize_product_name,
    is_valid_url,
)


def make_repository(
    repo_name="example-ai",
    owner_login="example-org",
    description="An AI-powered assistant",
    stars=500,
):
    return GitHubRepository(
        repo_id=123,
        name=repo_name,
        full_name=f"{owner_login}/{repo_name}",
        description=description,
        html_url=f"https://github.com/{owner_login}/{repo_name}",
        homepage="https://example.com",
        stars=stars,
        owner_login=owner_login,
        owner_type="Organization",
    )


def test_product_extraction():
    repository = make_repository()

    product = extract_product_candidate(repository)

    assert product is not None
    assert product.name == "example-ai"
    assert product.stars == 500
    assert product.verified_product is False


def test_product_name_normalization():
    assert normalize_product_name(
        "  AI   Assistant  "
    ) == "ai assistant"


def test_invalid_repository_url():
    repository = make_repository()

    repository.html_url = "invalid-url"

    product = extract_product_candidate(repository)

    assert product is None


def test_missing_description():
    repository = make_repository(description="")

    product = extract_product_candidate(repository)

    assert product is None


def test_duplicate_products():
    repositories = [
        make_repository(),
        make_repository(),
    ]

    products = extract_unique_product_candidates(
        repositories
    )

    assert len(products) == 1


def test_same_name_different_owners():
    repositories = [
        make_repository(owner_login="company-one"),
        make_repository(owner_login="company-two"),
    ]

    products = extract_unique_product_candidates(
        repositories
    )

    assert len(products) == 2


def test_url_validation():
    assert is_valid_url("https://example.com") is True
    assert is_valid_url("not-a-url") is False
    assert is_valid_url(None) is False


def test_negative_star_count():
    repository = make_repository(stars=-10)

    product = extract_product_candidate(repository)

    assert product is not None
    assert product.stars == 0