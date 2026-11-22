from ai_pipeline.services.resolution_worker import get_startup_name


def test_mock_extraction_rejected():
    data = {
        "results": [],
        "mock": True,
        "needs_review": True,
    }
    assert get_startup_name(data) is None


def test_real_extraction_supported():
    data = {
        "results": [
            {
                "entity_type": "startup",
                "startup": {
                    "name": "Example AI Labs",
                    "website": "https://example.com",
                },
            }
        ],
        "mock": False,
    }
    assert get_startup_name(data) == "Example AI Labs"


def test_invalid_startup_name_rejected():
    data = {
        "results": [
            {
                "entity_type": "startup",
                "startup": {"name": ""},
            }
        ],
        "mock": False,
    }
    assert get_startup_name(data) is None


def test_empty_results_rejected():
    assert get_startup_name({"results": [], "mock": False}) is None


def test_non_startup_entity_rejected():
    data = {
        "results": [
            {
                "entity_type": "product",
                "product": {"name": "Example Product"},
            }
        ],
        "mock": False,
    }
    assert get_startup_name(data) is None


def test_multiple_results():
    data = {
        "results": [
            {
                "entity_type": "product",
                "product": {"name": "Example Product"},
            },
            {
                "entity_type": "startup",
                "startup": {"name": "Second AI Startup"},
            },
        ],
        "mock": False,
    }
    assert get_startup_name(data) == "Second AI Startup"


def test_legacy_single_result_supported():
    data = {
        "entity_type": "startup",
        "startup": {"name": "Legacy Startup"},
    }
    assert get_startup_name(data) == "Legacy Startup"
