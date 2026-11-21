from fastapi import FastAPI

from ai_pipeline.config import settings


app = FastAPI(
    title=settings.APP_NAME,
    description="AI Intelligence Data Ingestion Pipeline",
    version="1.0.0"
)


@app.get("/")
async def root():

    return {
        "application": settings.APP_NAME,
        "version": "1.0.0",
        "message": "AI Intelligence Pipeline is running"
    }


@app.get("/health")
async def health():

    return {
        "status": "healthy",
        "service": "api"
    }