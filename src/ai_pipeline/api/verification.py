from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_pipeline.database.connection import get_db
from ai_pipeline.database.models import StartupVerificationRecord


router = APIRouter(
    prefix="/api/v1/verifications",
    tags=["Startup Verification"],
)


class VerificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_record_id: UUID
    candidate_name: str
    score: int
    status: str
    reasons: list[str]
    evidence: dict
    evaluated_at: str | None = None


class VerificationListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[VerificationResponse]


class VerificationSummaryResponse(BaseModel):
    total: int
    by_status: dict[str, int]


def serialize_verification(record):
    return VerificationResponse(
        id=record.id,
        source_record_id=record.source_record_id,
        candidate_name=record.candidate_name,
        score=record.score,
        status=record.status,
        reasons=record.reasons,
        evidence=record.evidence,
        evaluated_at=(
            record.evaluated_at.isoformat()
            if record.evaluated_at
            else None
        ),
    )


@router.get(
    "",
    response_model=VerificationListResponse,
)
async def list_verifications(
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db),
):
    """
    List preliminary startup verification results.

    Supports filtering and pagination.
    """

    query = select(StartupVerificationRecord)

    count_query = select(func.count()).select_from(
        StartupVerificationRecord
    )

    if status:
        query = query.where(
            StartupVerificationRecord.status == status
        )

        count_query = count_query.where(
            StartupVerificationRecord.status == status
        )

    total = await session.scalar(count_query)

    query = (
        query
        .order_by(
            StartupVerificationRecord.score.desc(),
            StartupVerificationRecord.id,
        )
        .limit(limit)
        .offset(offset)
    )

    result = await session.execute(query)

    records = result.scalars().all()

    return VerificationListResponse(
        total=total or 0,
        limit=limit,
        offset=offset,
        items=[
            serialize_verification(record)
            for record in records
        ],
    )


@router.get(
    "/summary",
    response_model=VerificationSummaryResponse,
)
async def verification_summary(
    session: AsyncSession = Depends(get_db),
):
    """
    Return verification counts grouped by status.
    """

    query = (
        select(
            StartupVerificationRecord.status,
            func.count(),
        )
        .group_by(StartupVerificationRecord.status)
    )

    result = await session.execute(query)

    counts = {
        status: count
        for status, count in result.all()
    }

    return VerificationSummaryResponse(
        total=sum(counts.values()),
        by_status=counts,
    )


@router.get(
    "/{verification_id}",
    response_model=VerificationResponse,
)
async def get_verification(
    verification_id: UUID,
    session: AsyncSession = Depends(get_db),
):
    """
    Retrieve one verification result by its UUID.
    """

    record = await session.get(
        StartupVerificationRecord,
        verification_id,
    )

    if record is None:
        raise HTTPException(
            status_code=404,
            detail="Verification record not found",
        )

    return serialize_verification(record)