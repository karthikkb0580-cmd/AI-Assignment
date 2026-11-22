from typing import Any


class EvidenceValidationError(Exception):
    """Raised when extracted evidence is missing or invalid."""


def validate_evidence(
    evidence: list[dict[str, Any]],
    source_text: str,
    source_url: str,
) -> bool:
    """
    Validate evidence returned by the LLM.

    Checks:
    1. Evidence is a non-empty list.
    2. Every evidence item is a dictionary.
    3. Every item has a valid field.
    4. Every quote exists in the original source.
    5. Every source URL matches the original source.

    Returns True when all evidence is valid.
    Raises EvidenceValidationError otherwise.
    """

    if not isinstance(evidence, list):
        raise EvidenceValidationError(
            "Evidence must be a list"
        )

    if not evidence:
        raise EvidenceValidationError(
            "Missing evidence"
        )

    if not isinstance(source_text, str):
        raise EvidenceValidationError(
            "Source text must be a string"
        )

    if not isinstance(source_url, str) or not source_url.strip():
        raise EvidenceValidationError(
            "Source URL must be a non-empty string"
        )

    for index, item in enumerate(evidence, start=1):

        if not isinstance(item, dict):
            raise EvidenceValidationError(
                f"Evidence item {index} must be a dictionary"
            )

        field = item.get("field")
        quote = item.get("quote")
        evidence_url = item.get("source_url")

        if not isinstance(field, str) or not field.strip():
            raise EvidenceValidationError(
                f"Evidence item {index} has an invalid field"
            )

        if not isinstance(quote, str) or not quote.strip():
            raise EvidenceValidationError(
                f"Evidence item {index} has an empty quote"
            )

        if quote not in source_text:
            raise EvidenceValidationError(
                f"Evidence item {index} contains an "
                f"unsupported quote: {quote[:100]}"
            )

        if evidence_url != source_url:
            raise EvidenceValidationError(
                f"Evidence item {index} has an incorrect source URL"
            )

    return True
