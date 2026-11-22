from ai_pipeline.services.normalization import (
    normalize_name,
    normalize_website,
    normalize_category,
)


def test_normalize_name():
    assert normalize_name("  NeuralForge AI  ") == "neuralforge ai"


def test_normalize_name_case():
    assert normalize_name("NEURALFORGE AI") == "neuralforge ai"


def test_normalize_name_empty():
    assert normalize_name("") is None


def test_normalize_website():
    assert (
        normalize_website("HTTPS://WWW.EXAMPLE.COM/")
        == "https://example.com"
    )


def test_normalize_website_query():
    assert (
        normalize_website("https://example.com/?utm_source=github")
        == "https://example.com"
    )


def test_normalize_website_missing_scheme():
    assert (
        normalize_website("example.com")
        == "https://example.com"
    )


def test_normalize_category():
    assert (
        normalize_category("  Artificial   Intelligence ")
        == "artificial intelligence"
    )