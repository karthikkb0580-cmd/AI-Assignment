from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_pipeline.database.models import Startup
from ai_pipeline.services.normalization import normalize_name


@dataclass
class MatchResult:
    matched: bool
    startup_id: str | None
    canonical_name: str | None
    match_method: str
    confidence_score: float


async def find_existing_startup(
    session: AsyncSession,
    name: str,
) -> MatchResult:
    """
    Find an existing startup by normalized name.

    This is an exact normalized-name match, not proof
    that two records represent the same real-world company.
    """

    normalized = normalize_name(name)

    if not normalized:
        return MatchResult(
            matched=False,
            startup_id=None,
            canonical_name=None,
            match_method="invalid_name",
            confidence_score=0.0,
        )

    statement = select(Startup).where(
        Startup.normalized_name == normalized
    )

    result = await session.execute(statement)

    startup = result.scalar_one_or_none()

    if startup is None:
        return MatchResult(
            matched=False,
            startup_id=None,
            canonical_name=None,
            match_method="no_match",
            confidence_score=0.0,
        )

    return MatchResult(
        matched=True,
        startup_id=str(startup.id),
        canonical_name=startup.name,
        match_method="exact_normalized_name",
        confidence_score=1.0,
    )