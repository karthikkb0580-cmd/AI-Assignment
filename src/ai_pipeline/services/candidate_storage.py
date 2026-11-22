import hashlib
import json
from dataclasses import asdict, is_dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_pipeline.database.models import SourceRecord


def candidate_to_dict(candidate: Any) -> dict:
    """
    Convert a candidate dataclass into a dictionary.
    """

    if not is_dataclass(candidate) or isinstance(candidate, type):
        raise TypeError("Candidate must be a dataclass instance")

    return asdict(candidate)


def generate_content_hash(data: dict) -> str:
    """
    Generate a stable SHA-256 hash.
    """

    serialized = json.dumps(
        data,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    return hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()


async def save_candidate(
    session: AsyncSession,
    candidate: Any,
    record_type: str,
) -> bool:
    """
    Save an unverified candidate to SourceRecord.

    Returns:
        True: New record inserted
        False: Exact record already exists
    """

    if record_type not in {"startup_candidate", "product_candidate"}:
        raise ValueError("Unsupported candidate record type")

    data = candidate_to_dict(candidate)

    source_url = (
        data.get("github_url")
        if record_type == "startup_candidate"
        else data.get("repository_url")
    )

    if not source_url:
        raise ValueError("Candidate source URL is required")

    # Include record type so startup and product candidates
    # can have distinct hashes even if their metadata overlaps.
    content_hash = generate_content_hash(
        {
            "record_type": record_type,
            "data": data,
        }
    )

    statement = select(SourceRecord.id).where(
        SourceRecord.source_url == source_url,
        SourceRecord.content_hash == content_hash,
    )

    existing = await session.scalar(statement)

    if existing is not None:
        return False

    record = SourceRecord(
        source_name="github",
        source_url=source_url,
        record_type=record_type,
        raw_content=json.dumps(
            data,
            ensure_ascii=False,
        ),
        raw_metadata=data,
        content_hash=content_hash,
        processing_status="pending_verification",
    )

    session.add(record)

    return True