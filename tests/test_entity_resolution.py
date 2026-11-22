import os
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
)

from ai_pipeline.database.models import (
    Base,
    EntityMapping,
    Startup,
)
from ai_pipeline.services.entity_resolution import resolve_startup


@pytest.mark.asyncio
async def test_resolve_existing_startup():

    database_url = os.getenv("TEST_DATABASE_URL")

    if not database_url:
        pytest.skip("TEST_DATABASE_URL not configured")

    if not database_url.endswith("/ai_intelligence_test"):
        raise RuntimeError("Refusing to use a non-test database")

    engine = create_async_engine(database_url)

    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        async with engine.connect() as connection:
            transaction = await connection.begin()

            try:
                session = AsyncSession(
                    bind=connection,
                    expire_on_commit=False,
                    join_transaction_mode="create_savepoint",
                )

                async with session:
                    unique_id = uuid.uuid4().hex[:8]
                    startup_name = f"NeuralForge {unique_id}"

                    startup = Startup(
                        id=uuid.uuid4(),
                        name=startup_name,
                        normalized_name=startup_name.casefold(),
                        source_url="https://example.com/startup",
                    )

                    session.add(startup)
                    await session.flush()

                    result = await resolve_startup(
                        session=session,
                        name=startup_name.upper(),
                        source_url="https://example.com/source",
                    )

                    await session.flush()

                    assert result.matched is True
                    assert result.startup_id == startup.id
                    assert result.needs_review is True

                    mappings = await session.scalars(
                        select(EntityMapping).where(
                            EntityMapping.startup_id == startup.id
                        )
                    )

                    assert len(mappings.all()) == 1

            finally:
                await transaction.rollback()

    finally:
        await engine.dispose()