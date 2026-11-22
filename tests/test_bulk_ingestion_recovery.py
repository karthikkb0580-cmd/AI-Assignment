import csv

import pytest

from ai_pipeline.services.bulk_ingestion import (
    BulkCSVIngestor,
    calculate_file_fingerprint,
    calculate_hash,
)


def make_ingestor(tmp_path):
    """
    Create a test ingestor with a temporary checkpoint file.
    """

    return BulkCSVIngestor(
        database_url="postgresql://test:test@localhost/test",
        batch_size=2,
        checkpoint_file=str(
            tmp_path / "checkpoint.json"
        ),
    )


def test_hash_is_deterministic():
    """
    Verify that identical normalized values produce
    identical SHA256 hashes.
    """

    first = calculate_hash(
        "Example Startup|https://example.com"
    )

    second = calculate_hash(
        "example startup|https://example.com"
    )

    assert first == second


def test_checkpoint_save_and_resume(tmp_path):
    """
    Verify that a checkpoint can be saved and loaded.
    """

    ingestor = make_ingestor(tmp_path)

    fingerprint = "test-fingerprint"

    assert ingestor.load_checkpoint(fingerprint) == 0

    ingestor.save_checkpoint(
        row_number=100,
        file_fingerprint=fingerprint,
    )

    assert ingestor.load_checkpoint(fingerprint) == 100


def test_checkpoint_rejects_different_file(tmp_path):
    """
    Verify that a checkpoint cannot be reused
    with a different dataset.
    """

    ingestor = make_ingestor(tmp_path)

    ingestor.save_checkpoint(
        row_number=100,
        file_fingerprint="original-file",
    )

    with pytest.raises(
        ValueError,
        match="Checkpoint does not match",
    ):
        ingestor.load_checkpoint("different-file")


def test_checkpoint_rejects_negative_row(tmp_path):
    """
    Verify that invalid negative checkpoint positions
    are rejected.
    """

    ingestor = make_ingestor(tmp_path)

    ingestor.save_checkpoint(
        row_number=-1,
        file_fingerprint="test-file",
    )

    with pytest.raises(
        ValueError,
        match="negative row number",
    ):
        ingestor.load_checkpoint("test-file")


def test_file_fingerprint_changes(tmp_path):
    """
    Verify that modifying the CSV changes its fingerprint.
    """

    csv_file = tmp_path / "startups.csv"

    csv_file.write_text(
        "name,website,source_url\n"
        "Startup A,https://a.com,https://source.com/a\n",
        encoding="utf-8",
    )

    first = calculate_file_fingerprint(csv_file)

    with csv_file.open(
        "a",
        encoding="utf-8",
    ) as file:
        file.write(
            "Startup B,https://b.com,https://source.com/b\n"
        )

    second = calculate_file_fingerprint(csv_file)

    assert first != second


def test_batch_size_validation(tmp_path):
    """
    Verify that invalid batch sizes are rejected.
    """

    with pytest.raises(
        ValueError,
        match="batch_size must be greater than zero",
    ):
        BulkCSVIngestor(
            database_url="postgresql://test:test@localhost/test",
            batch_size=0,
            checkpoint_file=str(
                tmp_path / "checkpoint.json"
            ),
        )


def test_csv_header_structure(tmp_path):
    """
    Verify the required CSV column structure.
    """

    csv_file = tmp_path / "test.csv"

    with csv_file.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.writer(file)

        writer.writerow([
            "name",
            "website",
            "source_url",
        ])

        writer.writerow([
            "Startup A",
            "https://a.com",
            "https://source.com/a",
        ])

    with csv_file.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:

        reader = csv.DictReader(file)

        assert reader.fieldnames == [
            "name",
            "website",
            "source_url",
        ]

        rows = list(reader)

        assert len(rows) == 1

        assert rows[0]["name"] == "Startup A"

        assert rows[0]["website"] == "https://a.com"

        assert rows[0]["source_url"] == (
            "https://source.com/a"
        )