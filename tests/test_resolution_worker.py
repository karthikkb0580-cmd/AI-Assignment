from ai_pipeline.services.resolution_worker import get_startup_name


def test_valid_startup():
    data = {
        "entity_type": "startup",
        "startup": {
            "name": "NeuralForge AI",
        },
        "needs_review": True,
    }

    assert get_startup_name(data) == "NeuralForge AI"


def test_mock_data_skipped():
    data = {
        "mock": True,
        "results": [],
        "needs_review": True,
    }

    assert get_startup_name(data) is None


def test_product_skipped():
    data = {
        "entity_type": "product",
        "product": {
            "name": "Example Product",
        },
    }

    assert get_startup_name(data) is None


def test_empty_name_skipped():
    data = {
        "entity_type": "startup",
        "startup": {
            "name": "   ",
        },
    }

    assert get_startup_name(data) is None


def test_invalid_data_skipped():
    assert get_startup_name(None) is None
    assert get_startup_name([]) is None
    assert get_startup_name({}) is None