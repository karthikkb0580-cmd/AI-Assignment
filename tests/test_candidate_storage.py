import pytest

from ai_pipeline.services.candidate_storage import (
    candidate_to_dict,
    generate_content_hash,
    save_candidate,
)

from ai_pipeline.services.startup_ingestion import (
    StartupCandidate,
)


def make_startup_candidate():
    return StartupCandidate(
        name="ExampleAI",
        github_url="https://github.com/example-ai",
        description="Example artificial intelligence startup",
        repository_url="https://github.com/example-ai/project",
        website="https://example.com",
        verified_company=False,
    )


def test_candidate_serialization():
    candidate = make_startup_candidate()

    data = candidate_to_dict(candidate)

    assert isinstance(data, dict)
    assert data["name"] == "ExampleAI"
    assert data["verified_company"] is False


def test_content_hash_is_deterministic():
    data = {
        "name": "ExampleAI",
        "website": "https://example.com",
    }

    first_hash = generate_content_hash(data)
    second_hash = generate_content_hash(data)

    assert first_hash == second_hash
    assert len(first_hash) == 64


def test_hash_ignores_dictionary_key_order():
    first = {
        "name": "ExampleAI",
        "website": "https://example.com",
    }

    second = {
        "website": "https://example.com",
        "name": "ExampleAI",
    }

    assert generate_content_hash(first) == generate_content_hash(second)


def test_hash_changes_when_content_changes():
    first = {"name": "ExampleAI", "stars": 100}
    second = {"name": "ExampleAI", "stars": 200}

    assert generate_content_hash(first) != generate_content_hash(second)


def test_non_dataclass_rejected():
    with pytest.raises(TypeError):
        candidate_to_dict({"name": "ExampleAI"})


@pytest.mark.asyncio
async def test_invalid_record_type_rejected():
    candidate = make_startup_candidate()

    with pytest.raises(ValueError, match="Unsupported"):
        await save_candidate(
            session=None,
            candidate=candidate,
            record_type="invalid_type",
        )