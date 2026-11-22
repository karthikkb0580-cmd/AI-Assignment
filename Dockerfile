FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
COPY pyproject.toml .

RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

RUN pip install --no-cache-dir --no-deps -e .

COPY alembic.ini ./alembic.ini
COPY alembic/ ./alembic/

RUN useradd --create-home --uid 10001 appuser
COPY scripts/ ./scripts/
USER appuser

EXPOSE 8000

CMD ["uvicorn", "ai_pipeline.main:app", "--host", "0.0.0.0", "--port", "8000"]