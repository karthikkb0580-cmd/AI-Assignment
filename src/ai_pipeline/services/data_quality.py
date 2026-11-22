from dataclasses import dataclass


@dataclass
class QualityResult:
    valid: bool
    reason: str


def validate_extraction(data: dict, source_text: str) -> QualityResult:
    if not isinstance(data, dict):
        return QualityResult(False, "Extraction must be a dictionary")

    if data.get("mock") is True:
        return QualityResult(False, "Mock extraction is not real data")

    results = data.get("results")

    if not isinstance(results, list):
        return QualityResult(False, "Missing results list")

    if not isinstance(source_text, str) or not source_text.strip():
        return QualityResult(False, "Source text is empty")

    for result in results:
        if not isinstance(result, dict):
            return QualityResult(False, "Invalid extraction item")

        if result.get("entity_type") != "startup":
            continue

        startup = result.get("startup")

        if not isinstance(startup, dict):
            return QualityResult(False, "Missing startup object")

        name = startup.get("name")

        if not isinstance(name, str) or not name.strip():
            return QualityResult(False, "Startup name is missing")

        if name.casefold() not in source_text.casefold():
            return QualityResult(
                False,
                "Startup name is not supported by source text",
            )

    return QualityResult(True, "Extraction passed basic validation")
