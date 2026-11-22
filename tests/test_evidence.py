import pytest

from ai_pipeline.llm.evidence import (
    EvidenceValidationError,
    validate_evidence,
)


SOURCE_TEXT = (
    "NeuralForge is an AI startup founded in 2023. "
    "It develops AI-powered tools for software developers."
)

SOURCE_URL = "https://example.com/neuralforge"


def test_valid_evidence():

    evidence = [
        {
            "field": "founded_year",
            "quote": "founded in 2023",
            "source_url": SOURCE_URL,
        }
    ]

    assert validate_evidence(
        evidence,
        SOURCE_TEXT,
        SOURCE_URL,
    )


def test_hallucinated_quote():

    evidence = [
        {
            "field": "founded_year",
            "quote": "founded in 2021",
            "source_url": SOURCE_URL,
        }
    ]

    with pytest.raises(EvidenceValidationError):
        validate_evidence(
            evidence,
            SOURCE_TEXT,
            SOURCE_URL,
        )


def test_wrong_source_url():

    evidence = [
        {
            "field": "founded_year",
            "quote": "founded in 2023",
            "source_url": "https://example.com/other",
        }
    ]

    with pytest.raises(EvidenceValidationError):
        validate_evidence(
            evidence,
            SOURCE_TEXT,
            SOURCE_URL,
        )


def test_missing_evidence():

    with pytest.raises(EvidenceValidationError):
        validate_evidence(
            [],
            SOURCE_TEXT,
            SOURCE_URL,
        )


def test_empty_quote():

    evidence = [
        {
            "field": "founded_year",
            "quote": "",
            "source_url": SOURCE_URL,
        }
    ]

    with pytest.raises(EvidenceValidationError):
        validate_evidence(
            evidence,
            SOURCE_TEXT,
            SOURCE_URL,
        )