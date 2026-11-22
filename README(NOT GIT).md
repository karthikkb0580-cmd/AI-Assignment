## Implemented Components

### Pipeline Orchestrator
File: scripts/run_pipeline.py

Coordinates extraction and resolution jobs.

Mock extraction is the default.

### Monitoring
File: scripts/pipeline_metrics.py

Reports:
- Source record count
- Extraction count
- Resolution job count
- Entity mapping count
- Startup count
- Extraction status distribution
- Resolution status distribution

### Data Quality
File: src/ai_pipeline/services/data_quality.py

Performs basic extraction validation.

This module is not yet enforced by the pipeline workers.

### Load Testing
File: scripts/load_test.py

Benchmarks extraction-name parsing without external API calls.

### Integration Tests
Files:
- tests/test_extraction_resolution_integration.py
- scripts/test_database_resolution.py
- scripts/test_full_pipeline.py

## Running the Pipeline

Mock mode:

    python scripts/run_pipeline.py --limit 5 --source-name bulk_csv

Real LLM mode:

    python scripts/run_pipeline.py --real --limit 5 --source-name bulk_csv

## Safety

- Mock results are excluded from resolution jobs.
- Startup verification is not automatic.
- Entity mappings require human review.
- Synthetic database tests use transaction rollback.

## Known Limitations

1. Resolution jobs currently operate per extraction, not per extracted entity.
2. The quality validator is not yet integrated into the workers.
3. The initial orchestrator lock implementation requires connection pinning for production use.
4. Parsing load tests do not measure end-to-end throughput.
5. Real LLM extraction has not been validated in this Step 16 test suite.
6. The orchestrator does not automatically run CSV ingestion or the bulk-to-source bridge.

## Next Steps

- Integrate data-quality checks into extraction and resolution.
- Implement per-entity resolution jobs.
- Add durable orchestration and concurrency tests.
- Add end-to-end load testing and observability.
