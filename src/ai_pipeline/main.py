from fastapi import FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from ai_pipeline.config import settings
from ai_pipeline.database.connection import AsyncSessionLocal
from ai_pipeline.api.verification import router as verification_router


app = FastAPI(
    title=settings.APP_NAME,
    description="AI Intelligence Data Ingestion Pipeline",
    version="1.0.0",
)

app.include_router(verification_router)

@app.get("/")
async def root():
    return {
        "application": settings.APP_NAME,
        "version": "1.0.0",
        "message": "AI Intelligence Pipeline is running",
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "api",
    }


@app.get("/health/database")
async def database_health():
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "database": "postgresql",
        }

    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail="Database unavailable",
        )