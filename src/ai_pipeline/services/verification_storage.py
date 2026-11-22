from sqlalchemy import select

from ai_pipeline.database.models import (
    SourceRecord,
    StartupVerificationRecord,
)
from ai_pipeline.services.startup_ingestion import StartupCandidate
from ai_pipeline.services.startup_verification import (
    verify_startup_candidate,
)


def candidate_from_source_record(record: SourceRecord) -> StartupCandidate:
    """Reconstruct a startup candidate from stored GitHub metadata."""

    if record.record_type != "startup_candidate":
        raise ValueError("Record is not a startup candidate")

    data = record.raw_metadata

    if not isinstance(data, dict):
        raise ValueError("Invalid candidate metadata")

    name = data.get("name")
    github_url = data.get("github_url")
    repository_url = data.get("repository_url")

    if not isinstance(name, str) or not name.strip():
        raise ValueError("Candidate name is missing")

    if not isinstance(github_url, str) or not github_url.strip():
        raise ValueError("GitHub organization URL is missing")

    if not isinstance(repository_url, str) or not repository_url.strip():
        raise ValueError("Repository URL is missing")

    return StartupCandidate(
        name=name,
        github_url=github_url,
        description=data.get("description"),
        repository_url=repository_url,
        website=data.get("website"),
        verified_company=False,
    )


async def save_verification_result(
    session,
    source_record_id,
    candidate: StartupCandidate,
):
    """Insert or update a preliminary verification result."""

    result = verify_startup_candidate(
        candidate,
        website_evidence=None,
    )

    query = select(StartupVerificationRecord).where(
        StartupVerificationRecord.source_record_id == source_record_id
    )

    existing = (await session.execute(query)).scalar_one_or_none()

    evidence = {
        "github_url": candidate.github_url,
        "repository_url": candidate.repository_url,
        "website": candidate.website,
        "website_checked": False,
        "independently_verified": False,
    }

    if existing is not None:
        existing.candidate_name = candidate.name
        existing.score = result.score
        existing.status = result.status.value
        existing.reasons = result.reasons
        existing.evidence = evidence

        await session.flush()
        return existing

    verification = StartupVerificationRecord(
        source_record_id=source_record_id,
        candidate_name=candidate.name,
        score=result.score,
        status=result.status.value,
        reasons=result.reasons,
        evidence=evidence,
    )

    session.add(verification)
    await session.flush()

    return verification