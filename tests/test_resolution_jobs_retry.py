"""
Step 13.5 — Resolution Job Retry Tests

Tests:
1. Exponential backoff calculation
2. Maximum retry attempts
3. Successful resolution
4. Mock record skipping

These are isolated unit tests.
They do not connect to PostgreSQL.
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_pipeline.services import resolution_jobs


def make_job(
    status="pending",
    attempt_count=0,
    next_retry_at=None,
):
    """Create a fake resolution job."""

    return SimpleNamespace(
        status=status,
        attempt_count=attempt_count,
        next_retry_at=next_retry_at,
        last_error=None,
        updated_at=None,
    )


def make_extraction(
    name="Test Startup",
    mock=False,
):
    """Create fake extracted startup data."""

    return SimpleNamespace(
        extracted_data={
            "entity_type": "startup",
            "mock": mock,
            "startup": {
                "name": name,
            },
        }
    )


def make_session(rows):
    """Create a mocked asynchronous database session."""

    session = MagicMock()

    result = MagicMock()
    result.all.return_value = rows

    session.execute = AsyncMock(return_value=result)
    session.flush = AsyncMock()

    # Simulate SQLAlchemy's nested transaction context manager.
    nested_transaction = MagicMock()
    nested_transaction.__aenter__ = AsyncMock()
    nested_transaction.__aexit__ = AsyncMock(return_value=False)

    session.begin_nested.return_value = nested_transaction

    return session


@pytest.mark.asyncio
async def test_exponential_backoff():
    """Failed jobs should receive increasing retry delays."""

    expected_delays = [30, 60, 120]

    for attempt, expected_delay in enumerate(
        expected_delays,
        start=1,
    ):
        job = make_job(
            status="pending",
            attempt_count=attempt - 1,
        )

        extraction = make_extraction()

        session = make_session(
            [(job, extraction, "https://example.com")]
        )

        with patch.object(
            resolution_jobs,
            "resolve_startup",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Simulated failure"),
        ):
            before = datetime.now(timezone.utc)

            stats = await resolution_jobs.process_resolution_jobs(
                session=session,
                batch_size=1,
            )

            after = datetime.now(timezone.utc)

        assert job.status == "retry"
        assert job.attempt_count == attempt
        assert stats["retry"] == 1
        assert job.last_error is not None

        assert job.next_retry_at is not None

        earliest = before + timedelta(seconds=expected_delay)
        latest = after + timedelta(seconds=expected_delay)

        assert earliest <= job.next_retry_at <= latest


@pytest.mark.asyncio
async def test_maximum_retry_attempts():
    """A job should permanently fail after four attempts."""

    job = make_job(
        status="retry",
        attempt_count=3,
        next_retry_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )

    extraction = make_extraction()

    session = make_session(
        [(job, extraction, "https://example.com")]
    )

    with patch.object(
        resolution_jobs,
        "resolve_startup",
        new_callable=AsyncMock,
        side_effect=RuntimeError("Simulated failure"),
    ):
        stats = await resolution_jobs.process_resolution_jobs(
            session=session,
            batch_size=1,
        )

    assert job.status == "failed"
    assert job.attempt_count == 4
    assert job.next_retry_at is None
    assert stats["failed"] == 1
    assert stats["retry"] == 0


@pytest.mark.asyncio
async def test_successful_resolution():
    """Successful resolution should complete the job."""

    job = make_job(
        status="retry",
        attempt_count=1,
        next_retry_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )

    extraction = make_extraction()

    session = make_session(
        [(job, extraction, "https://example.com")]
    )

    fake_resolution = SimpleNamespace(
        matched=True,
        startup_id="test-startup-id",
    )

    with patch.object(
        resolution_jobs,
        "resolve_startup",
        new_callable=AsyncMock,
        return_value=fake_resolution,
    ):
        stats = await resolution_jobs.process_resolution_jobs(
            session=session,
            batch_size=1,
        )

    assert job.status == "completed"
    assert job.attempt_count == 2
    assert job.last_error is None
    assert job.next_retry_at is None
    assert stats["matched"] == 1
    assert stats["failed"] == 0


@pytest.mark.asyncio
async def test_mock_record_skipping():
    """Mock extraction records should be skipped."""

    job = make_job()

    extraction = make_extraction(
        name="Mock Startup",
        mock=True,
    )

    session = make_session(
        [(job, extraction, "https://example.com")]
    )

    with patch.object(
        resolution_jobs,
        "resolve_startup",
        new_callable=AsyncMock,
    ) as mock_resolve:
        stats = await resolution_jobs.process_resolution_jobs(
            session=session,
            batch_size=1,
        )

    assert job.status == "skipped"
    assert job.attempt_count == 0
    assert job.next_retry_at is None
    assert stats["skipped"] == 1

    mock_resolve.assert_not_awaited()