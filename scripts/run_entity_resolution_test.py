import os
import pytest

from sqlalchemy.engine import make_url


def main():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")

    url = make_url(database_url)

    if url.database != "ai_intelligence":
        raise RuntimeError(
            "Unexpected main database. Refusing to run."
        )

    test_url = url.set(database="ai_intelligence_test")

    os.environ["TEST_DATABASE_URL"] = (
        test_url.render_as_string(hide_password=False)
    )

    print("Using isolated test database: ai_intelligence_test")

    return pytest.main(
        [
            "tests/test_entity_resolution.py",
            "tests/test_resolution_worker_integration.py",
            "-v",
            "-p",
            "no:cacheprovider",
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())