# AI Intelligence Pipeline — Performance Report

## 1. Overview

This report documents the performance and database health of the AI Intelligence Pipeline.

The pipeline supports bulk data ingestion, PostgreSQL storage, structured LLM extraction, data-quality validation, and entity resolution.

## 2. Bulk Ingestion Benchmark

Previous measured results:

| Metric | Result |
|---|---|
| Input records | 100,000 |
| Newly inserted records | 99,000 |
| Duplicate records | 1,000 |
| Execution time | 8.19 seconds |
| Throughput | Approximately 12,213 records/second |

These results were obtained using synthetic test data.

## 3. In-Memory Parsing Benchmark

Previous measured results:

| Metric | Result |
|---|---|
| Records processed | 100,000 |
| Execution time | 0.0792 seconds |
| Throughput | Approximately 1,263,026 records/second |

This benchmark measures in-memory parsing rather than end-to-end database ingestion.

## 4. Database Performance

Update after running the database performance script.

- Database query latency: Pending
- Database size: Pending
- Largest table: Pending
- Total bulk startup records: Pending

## 5. Extraction and Resolution Metrics

Previously observed:

- Source records: 71
- Extraction records: 26
- Completed extractions: 25
- Failed extractions: 1
- Resolution jobs: 25
- Entity mappings: 0

These figures are a historical snapshot and may change.

## 6. Reliability Features

The pipeline includes:

- Duplicate prevention
- Checkpoint-based ingestion recovery
- Extraction retry handling
- Resolution-job retry handling
- PostgreSQL advisory locking
- Transaction rollback in integration tests
- Basic source-grounded extraction validation

## 7. Limitations

The benchmark results do not establish production-scale LLM throughput.

The synthetic bulk dataset does not represent verified startup information.

Real LLM extraction, concurrent lock contention, and large-scale end-to-end processing require separate verification.

## 8. Conclusion

The pipeline has demonstrated high-throughput synthetic bulk ingestion and successful database integration tests.

Further testing is required to establish real-world extraction accuracy, operational reliability, and sustained production performance.