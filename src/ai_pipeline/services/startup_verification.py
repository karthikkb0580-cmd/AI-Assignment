import re

from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urlsplit

from ai_pipeline.services.startup_ingestion import StartupCandidate
from ai_pipeline.services.website_verification import WebsiteEvidence


class VerificationStatus(str, Enum):
    NEEDS_REVIEW = "needs_review"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    REJECTED = "rejected"


@dataclass
class StartupVerificationResult:
    name: str
    github_url: str
    website: str | None
    score: int
    status: VerificationStatus
    reasons: list[str] = field(default_factory=list)

    @property
    def verified(self) -> bool:
        """
        Automated evidence scoring never verifies a company.

        Independent verification is required before a startup
        can be marked as verified.
        """
        return False


def normalize_text(value: str | None) -> str:
    """
    Normalize text for basic name comparison.

    Example:
        "Example AI" -> "exampleai"
        "EXAMPLE-AI" -> "exampleai"
    """

    if not value:
        return ""

    return "".join(
        character.lower()
        for character in value
        if character.isalnum()
    )


def is_valid_github_organization_url(
    url: str | None,
) -> bool:
    """
    Validate the structure of a GitHub organization URL.

    Valid:
        https://github.com/example-ai

    Invalid:
        https://github.com/example-ai/project
        https://github.com.evil.com/example-ai
        https://user:password@github.com/example-ai
        http://github.com/example-ai

    Note:
        This validates URL structure only.
        It does not prove the account is an organization.
    """

    if not isinstance(url, str) or not url:
        return False

    if url != url.strip():
        return False

    if any(ord(char) < 32 or ord(char) == 127 for char in url):
        return False

    try:
        parsed = urlsplit(url)

        if parsed.scheme != "https":
            return False

        if parsed.hostname != "github.com":
            return False

        if parsed.username is not None:
            return False

        if parsed.password is not None:
            return False

        if parsed.port is not None:
            return False

        if parsed.query or parsed.fragment:
            return False

        if parsed.path.endswith("/"):
            return False

        parts = parsed.path.strip("/").split("/")

        if len(parts) != 1:
            return False

        organization = parts[0]

        if not organization:
            return False

        if len(organization) > 39:
            return False

        if "--" in organization:
            return False

        return bool(
            re.fullmatch(
                r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?",
                organization,
            )
        )

    except ValueError:
        return False


def extract_domain(url: str | None) -> str | None:
    """
    Extract the hostname from a URL.

    Example:
        https://www.example.com/about
        -> www.example.com
    """

    if not url:
        return None

    try:
        parsed = urlsplit(url)

        if parsed.scheme not in {"http", "https"}:
            return None

        return parsed.hostname

    except ValueError:
        return None


def is_consistent_website_evidence(
    candidate: StartupCandidate,
    evidence: WebsiteEvidence | None,
) -> bool:
    """
    Ensure the supplied evidence belongs to the candidate URL.

    This prevents unrelated website evidence from being used
    to increase the candidate's score.

    A redirect may lead to a different final domain, so
    this check validates the original requested URL.
    """

    if evidence is None:
        return False

    if not candidate.website:
        return False

    if not evidence.url:
        return False

    candidate_domain = extract_domain(candidate.website)
    evidence_domain = extract_domain(evidence.url)

    if not candidate_domain or not evidence_domain:
        return False

    return candidate_domain.lower() == evidence_domain.lower()


def verify_startup_candidate(
    candidate: StartupCandidate,
    website_evidence: WebsiteEvidence | None = None,
) -> StartupVerificationResult:
    """
    Evaluate preliminary evidence for a GitHub startup candidate.

    Scoring:
        Valid GitHub organization URL: 20
        Organization description:     10
        Website URL:                  10
        Website reachable:           25
        Website title:               10
        Name matches website title:  25

    Maximum score: 100

    Decision:
        70-100: needs_review
        0-69:   insufficient_evidence

    Invalid GitHub URL or missing organization name:
        rejected

    IMPORTANT:
        A high score does not mean the startup is verified.
        Independent evidence is required for verification.
    """

    reasons: list[str] = []
    score = 0

    name = candidate.name or ""
    github_url = candidate.github_url or ""
    website = candidate.website

    if not name.strip():
        return StartupVerificationResult(
            name=name,
            github_url=github_url,
            website=website,
            score=0,
            status=VerificationStatus.REJECTED,
            reasons=["Missing organization name"],
        )

    if not is_valid_github_organization_url(github_url):
        return StartupVerificationResult(
            name=name,
            github_url=github_url,
            website=website,
            score=0,
            status=VerificationStatus.REJECTED,
            reasons=["Invalid GitHub organization URL"],
        )

    score += 20
    reasons.append("Valid GitHub organization URL structure")

    if candidate.description and candidate.description.strip():
        score += 10
        reasons.append("Organization description available")

    if website:
        from ai_pipeline.services.website_verification import (
            is_valid_public_url,
        )

        if is_valid_public_url(website):
            score += 10
            reasons.append("Public website URL provided")
        else:
            reasons.append("Website URL is invalid or unsafe")

    evidence_matches = is_consistent_website_evidence(
        candidate,
        website_evidence,
    )

    if website_evidence is not None and not evidence_matches:
        reasons.append(
            "Website evidence does not match candidate website"
        )

    if evidence_matches and website_evidence is not None:

        if website_evidence.reachable:
            score += 25
            reasons.append("Website is reachable")

            if website_evidence.title:
                score += 10
                reasons.append("Website title available")

                normalized_name = normalize_text(name)
                normalized_title = normalize_text(
                    website_evidence.title
                )

                if (
                    normalized_name
                    and normalized_name in normalized_title
                ):
                    score += 25
                    reasons.append(
                        "Organization name matches website title"
                    )
                else:
                    reasons.append(
                        "Organization name not found in website title"
                    )

        else:
            reasons.append("Website is not reachable")

    score = min(score, 100)

    if score >= 70:
        status = VerificationStatus.NEEDS_REVIEW
    else:
        status = VerificationStatus.INSUFFICIENT_EVIDENCE

    return StartupVerificationResult(
        name=name,
        github_url=github_url,
        website=website,
        score=score,
        status=status,
        reasons=reasons,
    )