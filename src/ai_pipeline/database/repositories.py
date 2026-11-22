import hashlib
import re
import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ai_pipeline.database.models import (
    EntityMapping,
    Job,
    News,
    Product,
    ResearchPaper,
    SourceRecord,
    Startup,
)


def normalize_name(name: str) -> str:
    normalized = name.strip().casefold()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def create_content_hash(content: str) -> str:
    return hashlib.sha256(
        content.encode("utf-8")
    ).hexdigest()


async def create_startup(
    session: AsyncSession,
    *,
    name: str,
    source_url: str,
    website: str | None = None,
    description: str | None = None,
    industry: str | None = None,
    headquarters: str | None = None,
    founded_year: int | None = None,
    employee_count: int | None = None,
) -> Startup:

    normalized = normalize_name(name)

    statement = (
        insert(Startup)
        .values(
            id=uuid.uuid4(),
            name=name,
            normalized_name=normalized,
            source_url=source_url,
            website=website,
            description=description,
            industry=industry,
            headquarters=headquarters,
            founded_year=founded_year,
            employee_count=employee_count,
        )
        .on_conflict_do_nothing(
            index_elements=["normalized_name"]
        )
        .returning(Startup)
    )

    result = await session.execute(statement)
    startup = result.scalar_one_or_none()

    if startup is None:
        result = await session.execute(
            select(Startup).where(
                Startup.normalized_name == normalized
            )
        )
        startup = result.scalar_one()

    await session.commit()
    return startup


async def get_startup_by_name(
    session: AsyncSession,
    name: str,
) -> Startup | None:

    normalized = normalize_name(name)

    result = await session.execute(
        select(Startup).where(
            Startup.normalized_name == normalized
        )
    )

    return result.scalar_one_or_none()


async def create_product(
    session: AsyncSession,
    *,
    name: str,
    source_url: str,
    startup_id: uuid.UUID | None = None,
    description: str | None = None,
    website: str | None = None,
    category: str | None = None,
    pricing_model: str | None = None,
) -> Product:

    normalized = normalize_name(name)

    statement = (
        insert(Product)
        .values(
            id=uuid.uuid4(),
            name=name,
            normalized_name=normalized,
            source_url=source_url,
            startup_id=startup_id,
            description=description,
            website=website,
            category=category,
            pricing_model=pricing_model,
        )
        .on_conflict_do_nothing(
            constraint="uq_products_name_source"
        )
        .returning(Product)
    )

    result = await session.execute(statement)
    product = result.scalar_one_or_none()

    if product is None:
        result = await session.execute(
            select(Product).where(
                Product.normalized_name == normalized,
                Product.source_url == source_url,
            )
        )
        product = result.scalar_one()

    await session.commit()
    return product


async def create_source_record(
    session: AsyncSession,
    *,
    source_name: str,
    source_url: str,
    record_type: str,
    raw_content: str,
    raw_metadata: dict | None = None,
) -> SourceRecord:

    content_hash = create_content_hash(raw_content)

    statement = (
        insert(SourceRecord)
        .values(
            id=uuid.uuid4(),
            source_name=source_name,
            source_url=source_url,
            record_type=record_type,
            raw_content=raw_content,
            raw_metadata=raw_metadata or {},
            content_hash=content_hash,
            processing_status="PENDING",
        )
        .on_conflict_do_nothing(
            constraint="uq_source_records_url_hash"
        )
        .returning(SourceRecord)
    )

    result = await session.execute(statement)
    record = result.scalar_one_or_none()

    if record is None:
        result = await session.execute(
            select(SourceRecord).where(
                SourceRecord.source_url == source_url,
                SourceRecord.content_hash == content_hash,
            )
        )
        record = result.scalar_one()

    await session.commit()
    return record