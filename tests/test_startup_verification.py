from ai_pipeline.services.startup_ingestion import StartupCandidate

from ai_pipeline.services.startup_verification import (
    VerificationStatus,
    verify_startup_candidate,
)

from ai_pipeline.services.website_verification import WebsiteEvidence


def make_candidate():
    return StartupCandidate(
        name="ExampleAI",
        github_url="https://github.com/example-ai",
        description="Artificial intelligence company",
        repository_url="https://github.com/example-ai/project",
        website="https://example.com",
        verified_company=False,
    )


def make_website_evidence(
    reachable=True,
    title="ExampleAI - Artificial Intelligence",
):
    return WebsiteEvidence(
        url="https://example.com",
        reachable=reachable,
        status_code=200 if reachable else 404,
        final_url="https://example.com",
        title=title,
        error=None,
    )


def test_strong_evidence_requires_review():
    candidate = make_candidate()
    evidence = make_website_evidence()

    result = verify_startup_candidate(candidate, evidence)

    assert result.score == 100
    assert result.status == VerificationStatus.NEEDS_REVIEW


def test_missing_website_evidence():
    candidate = make_candidate()

    result = verify_startup_candidate(candidate, None)

    assert result.score == 40
    assert result.status == VerificationStatus.INSUFFICIENT_EVIDENCE


def test_unreachable_website():
    candidate = make_candidate()
    evidence = make_website_evidence(
        reachable=False,
        title=None,
    )

    result = verify_startup_candidate(candidate, evidence)

    assert result.score == 40
    assert result.status == VerificationStatus.INSUFFICIENT_EVIDENCE


def test_missing_organization_name():
    candidate = make_candidate()
    candidate.name = ""

    result = verify_startup_candidate(candidate, None)

    assert result.score == 0
    assert result.status == VerificationStatus.REJECTED


def test_invalid_github_url():
    candidate = make_candidate()
    candidate.github_url = "https://example.com/fake"

    result = verify_startup_candidate(candidate, None)

    assert result.status == VerificationStatus.REJECTED


def test_name_does_not_match_website_title():
    candidate = make_candidate()
    evidence = make_website_evidence(
        title="Different Company"
    )

    result = verify_startup_candidate(candidate, evidence)

    assert result.score == 75
    assert result.status == VerificationStatus.NEEDS_REVIEW