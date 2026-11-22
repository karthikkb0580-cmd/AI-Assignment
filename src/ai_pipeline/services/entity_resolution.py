from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_pipeline.database.models import EntityMapping
from ai_pipeline.services.deduplication import find_existing_startup
from ai_pipeline.services.normalization import normalize_name


@dataclass
class ResolutionResult:
    matched: bool
    startup_id: UUID | None
    canonical_name: str
    match_method: str
    confidence_score: float
    needs_review: bool = True


async def resolve_startup(
    session: AsyncSession,
    name: str,
    source_url: str,
) -> ResolutionResult:
    """
    Match an extracted startup to an existing startup.

    Records the match in entity_mappings.

    Does not automatically create or verify startups.
    """

    normalized = normalize_name(name)

    if not normalized:
        raise ValueError("Startup name cannot be empty")

    if not source_url or not source_url.strip():
        raise ValueError("Source URL cannot be empty")

    match = await find_existing_startup(
        session=session,
        name=name,
    )

    startup_id = (
        UUID(match.startup_id)
        if match.startup_id
        else None
    )

    canonical_name = (
        match.canonical_name
        if match.matched
        else name.strip()
    )

    # Prevent duplicate mappings for the same source/name.
    existing_statement = select(EntityMapping).where(
        EntityMapping.normalized_name == normalized,
        EntityMapping.source_url == source_url,
    )

    existing_result = await session.execute(
        existing_statement
    )

    existing_mapping = existing_result.scalar_one_or_none()

    if existing_mapping is None:
        mapping = EntityMapping(
            raw_name=name,
            normalized_name=normalized,
            canonical_name=canonical_name,
            startup_id=startup_id,
            match_method=match.match_method,
            confidence_score=(
                match.confidence_score
                if match.matched
                else 0.0
            ),
            source_url=source_url,
        )

        session.add(mapping)

    return ResolutionResult(
        matched=match.matched,
        startup_id=startup_id,
        canonical_name=canonical_name,
        match_method=match.match_method,
        confidence_score=(
            match.confidence_score
            if match.matched
            else 0.0
        ),
        needs_review=True,
    )