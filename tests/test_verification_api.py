import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from ai_pipeline.api.verification import router


@pytest.mark.asyncio
async def test_verification_api_validation():
    app = FastAPI()
    app.include_router(router)

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/api/v1/verifications",
            params={"limit": 0},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_verification_api_invalid_uuid():
    app = FastAPI()
    app.include_router(router)

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/api/v1/verifications/not-a-uuid"
        )

    assert response.status_code == 422