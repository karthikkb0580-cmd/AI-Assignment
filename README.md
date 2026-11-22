# AI Intelligence Pipeline

### Scalable Data Ingestion, Structured LLM Extraction & Entity Resolution

A Python-based data intelligence pipeline designed to ingest, normalize, and process startup ecosystem information.

The project was developed as a technical assessment inspired by the data engineering challenges faced by GraphOne / FrontierAtlas.

It demonstrates bulk ingestion, fault-tolerant extraction, database-backed processing, duplicate prevention, and entity resolution.

---

## 1. Project Overview

Modern startup intelligence platforms collect information from multiple sources, including company websites, GitHub repositories, research publications, and news articles.

Processing these sources introduces several challenges:

- Large-scale data ingestion
- Duplicate records
- Unstructured source content
- LLM API failures
- Rate limiting
- Structured data validation
- Startup name normalization
- Entity matching
- Database consistency
- Recovery after interrupted processing

This project addresses these challenges using a modular pipeline architecture.

## 2. System Architecture

```text
                   DATA SOURCES
                        |
                        v
                 DATA INGESTION
                        |
                        v
               RAW DATA STORAGE
                  PostgreSQL
                        |
                        v
                SOURCE RECORDS
                        |
                        v
                LLM EXTRACTION
                        |
                        v
              STRUCTURED JSON DATA
                        |
                        v
             DATA QUALITY VALIDATION
                        |
                        v
               EXTRACTION RESULTS
                        |
                        v
                RESOLUTION JOBS
                        |
                        v
               ENTITY RESOLUTION
                        |
                        v
                ENTITY MAPPINGS
                        |
                        v
                 HUMAN REVIEW
```

## 3. Technology Stack

| Component | Technology |
|---|---|
| Programming language | Python |
| Database | PostgreSQL |
| ORM | SQLAlchemy Async |
| API framework | FastAPI |
| Data validation | Pydantic |
| Containerization | Docker Compose |
| Testing | Pytest |
| LLM integration | Configurable LLM API |
| Database migrations | Alembic |

## 4. Core Features

### 4.1 Bulk Data Ingestion

The system supports large-scale ingestion of startup records.

Implemented capabilities include:

- Batch processing
- Duplicate detection
- Checkpoint-based recovery
- PostgreSQL persistence
- High-throughput synthetic data testing

A previous benchmark processed 100,000 synthetic input records, including 1,000 duplicates.

### 4.2 Structured LLM Extraction

The extraction worker supports:

- Real LLM extraction
- Mock extraction for development
- Structured output
- Extraction status tracking
- Retry attempts
- Persistent extraction results

Real LLM extraction requires valid API credentials.

### 4.3 Data Quality Validation

The pipeline includes basic source-grounding checks.

For startup entities, the validator checks that the extracted startup name appears in the source content.

Invalid results can be rejected before being stored as completed extractions.

This validation does not independently verify every extracted field.

### 4.4 Entity Resolution

The entity-resolution system supports:

- Startup name normalization
- Existing-startup matching
- Confidence scores
- Entity mapping creation
- Duplicate mapping prevention
- Human-review flags

Unmatched names are marked for review rather than automatically treated as verified startups.

### 4.5 Fault Tolerance

The project includes:

- Extraction retry handling
- Resolution-job retries
- Database transactions
- Duplicate prevention
- Checkpoint recovery
- PostgreSQL advisory locking

### 4.6 Monitoring

The project includes scripts for:

- Pipeline metrics
- Extraction quality auditing
- Database performance inspection
- Synthetic performance benchmarking

---

## 5. Installation

### Prerequisites

- Python
- Docker Desktop
- Docker Compose
- Git

### Clone the repository

```bash
git clone <YOUR_REPOSITORY_URL>
cd AI-Intelligence-Pipeline
```

### Configure environment variables

Create a `.env` file using the project's environment configuration.

For real LLM extraction, configure:

```dotenv
LLM_API_KEY=your_api_key
LLM_BASE_URL=your_provider_api_base_url
LLM_MODEL=your_model_name
```

Database configuration must also match the Docker Compose setup.

Never commit real credentials.

### Start Docker services

```bash
docker compose up -d
```

---

## 6. Running the Pipeline

### Mock extraction

Mock mode allows testing without making LLM API requests.

```bash
docker compose run --rm api python scripts/run_pipeline.py --limit 5
```

### Real LLM extraction

```bash
docker compose run --rm api python scripts/run_pipeline.py --real --limit 1
```

Real extraction requires correctly configured LLM credentials.

### Source-specific processing

```bash
docker compose run --rm api python scripts/run_pipeline.py --limit 5 --source-name github
```

### Available options

| Option | Purpose |
|---|---|
| `--limit` | Maximum source records selected |
| `--batch-size` | Entity-resolution batch size |
| `--max-attempts` | Maximum extraction attempts |
| `--source-name` | Filter by source |
| `--real` | Enable real LLM extraction |

---

## 7. Testing

Run the complete test suite:

```bash
python -m pytest tests/ -q
```

The project includes tests for:

- Data quality
- Database resolution
- Duplicate prevention
- Pipeline integration
- Extraction behavior
- Other pipeline components

Previously verified results:

- 103 passing tests and 2 skipped tests in the full suite.
- 5 passing data-quality tests in a later targeted run.
- Successful database-resolution integration tests.
- Successful full-pipeline integration tests.

A final full-suite regression run should be recorded before submission.

---

## 8. Performance Results

### Bulk ingestion

| Metric | Measured result |
|---|---:|
| Input records | 100,000 |
| New records | 99,000 |
| Duplicates | 1,000 |
| Duration | 8.19 seconds |
| Throughput | Approximately 12,213 records/second |

### In-memory parsing

| Metric | Measured result |
|---|---:|
| Records processed | 100,000 |
| Duration | 0.0792 seconds |
| Throughput | Approximately 1,263,026 records/second |

These benchmarks measure different operations.

The parsing benchmark does not represent database ingestion or real LLM throughput.

---

## 9. Database Design

The pipeline uses the following main tables:

| Table | Purpose |
|---|---|
| `bulk_startup_records` | Bulk ingestion storage |
| `source_records` | Source content |
| `extraction_results` | Structured extraction output |
| `resolution_jobs` | Entity-resolution processing |
| `startups` | Canonical startup records |
| `entity_mappings` | Raw-to-canonical entity mappings |

Database constraints help prevent duplicate records and mappings.

---

## 10. Project Structure

```text
AI-Intelligence-Pipeline/
|
|-- src/
|   `-- ai_pipeline/
|       |-- database/
|       |-- llm/
|       `-- services/
|
|-- scripts/
|   |-- run_pipeline.py
|   |-- run_extraction.py
|   |-- audit_extractions.py
|   |-- pipeline_metrics.py
|   |-- database_performance.py
|   |-- load_test.py
|   |-- test_database_resolution.py
|   `-- test_full_pipeline.py
|
|-- tests/
|
|-- docker-compose.yml
|-- pyproject.toml
|-- README.md
`-- .gitignore
```

Some additional ingestion and migration files are omitted from this simplified structure.

---

## 11. Reliability and Idempotency

The system is designed to reduce duplicate processing.

Extraction results are identified using source-record information, content hashes, and extractor versions.

Resolution jobs are associated with extraction results.

Database uniqueness constraints and conflict-handling logic help prevent duplicate records.

The pipeline also uses PostgreSQL advisory locking to reduce overlapping orchestrator executions.

---

## 12. Current Limitations

The following areas require additional work before production deployment:

1. Real LLM end-to-end processing requires separate verification.
2. Synthetic startup records are not verified company data.
3. Data-quality validation currently provides basic source grounding.
4. Multi-startup resolution is not fully supported.
5. Sustained production-scale LLM throughput has not been measured.
6. Unmatched startup names require review.
7. Concurrent advisory-lock contention should be verified separately.

---

## 13. Future Improvements

Potential improvements include:

- Distributed background workers
- Better source evidence verification
- Multi-entity extraction and resolution
- Human-review dashboard
- Automated scheduling
- Monitoring dashboards
- Additional source connectors
- Improved startup matching
- Larger real-world performance benchmarks

---

## 14. Conclusion

The AI Intelligence Pipeline demonstrates a modular approach to building a data intelligence system.

It combines high-throughput synthetic ingestion, persistent extraction processing, basic data-quality checks, and database-backed entity resolution.

The project provides a foundation for further development of startup ecosystem intelligence infrastructure.