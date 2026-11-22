import hashlib

from ai_pipeline.database.models import Base
from ai_pipeline.database.repositories import (
    create_content_hash,
    normalize_name,
)


def test_normalize_name():

    assert normalize_name("  OpenAI  ") == "openai"
    assert normalize_name("Open   AI") == "open ai"


def test_content_hash():

    content = "AI Intelligence Pipeline"

    expected = hashlib.sha256(
        content.encode("utf-8")
    ).hexdigest()

    assert create_content_hash(content) == expected


def test_database_tables_exist_in_metadata():

    expected_tables = {
        "startups",
        "products",
        "research_papers",
        "jobs",
        "news",
        "source_records",
        "entity_mappings",
    }

    assert expected_tables.issubset(
        set(Base.metadata.tables.keys())
    )


def test_startups_have_unique_normalized_name():

    table = Base.metadata.tables["startups"]

    assert table.c.normalized_name.unique is True


def test_research_papers_have_unique_url():

    table = Base.metadata.tables["research_papers"]

    assert table.c.paper_url.unique is True