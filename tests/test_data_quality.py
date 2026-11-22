from ai_pipeline.services.data_quality import validate_extraction


def test_valid_startup():
    data = {
        "mock": False,
        "results": [
            {
                "entity_type": "startup",
                "startup": {"name": "Example AI Labs"},
            }
        ],
    }

    result = validate_extraction(
        data,
        "Example AI Labs builds AI software.",
    )

    assert result.valid is True


def test_mock_rejected():
    data = {
        "mock": True,
        "results": [],
    }

    result = validate_extraction(data, "Example source")

    assert result.valid is False


def test_unsupported_name_rejected():
    data = {
        "mock": False,
        "results": [
            {
                "entity_type": "startup",
                "startup": {"name": "Invented Startup"},
            }
        ],
    }

    result = validate_extraction(
        data,
        "This text does not mention a company.",
    )

    assert result.valid is False


def test_empty_source_rejected():
    data = {
        "mock": False,
        "results": [],
    }

    result = validate_extraction(data, "")

    assert result.valid is False

from ai_pipeline.services.data_quality import validate_extraction


def test_rejects_hallucinated_startup_name():
    source_text = (
        "Acme Robotics develops warehouse automation software."
    )

    extracted_data = {
        "results": [
            {
                "entity_type": "startup",
                "startup": {
                    "name": "Imaginary AI Corporation",
                },
            }
        ],
        "mock": False,
    }

    result = validate_extraction(
        data=extracted_data,
        source_text=source_text,
    )

    assert result.valid is False
    assert (
        result.reason
        == "Startup name is not supported by source text"
    )
