import argparse
import csv
import time
from pathlib import Path


def generate_dataset(
    output_file: str,
    total_records: int = 100000,
    duplicate_every: int = 100,
):
    if total_records < 1:
        raise ValueError("total_records must be positive")

    if duplicate_every < 0:
        raise ValueError("duplicate_every cannot be negative")

    output_path = Path(output_file)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    started_at = time.perf_counter()
    duplicates = 0

    print("=" * 55)
    print("GENERATING SYNTHETIC STARTUP DATASET")
    print("=" * 55)

    print(f"Total records: {total_records:,}")
    print(f"Output file: {output_path}")
    print()

    with output_path.open(
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

        for index in range(1, total_records + 1):

            record_id = index

            # Every Nth record duplicates the previous record.
            if duplicate_every and index % duplicate_every == 0:
                record_id = index - 1
                duplicates += 1

            name = f"Synthetic AI Startup {record_id:06d}"

            website = (
                f"https://startup-{record_id:06d}.example.com"
            )

            source_url = (
                f"https://source.example.com/startups/{index}"
            )

            writer.writerow([
                name,
                website,
                source_url,
            ])

            if index % 10000 == 0:
                print(
                    f"Generated {index:,}/{total_records:,} records"
                )

    duration = time.perf_counter() - started_at

    print()
    print("=" * 55)
    print("DATASET GENERATION COMPLETED")
    print("=" * 55)

    print(f"Total records: {total_records:,}")
    print(f"Intentional duplicates: {duplicates:,}")
    print(f"Expected unique records: {total_records - duplicates:,}")
    print(f"Duration: {duration:.2f} seconds")

    print("=" * 55)


def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic startup CSV dataset"
    )

    parser.add_argument(
        "--output",
        default="data/startups_100k.csv",
        help="Output CSV file",
    )

    parser.add_argument(
        "--records",
        type=int,
        default=100000,
        help="Number of records to generate",
    )

    parser.add_argument(
        "--duplicate-every",
        type=int,
        default=100,
        help="Insert one duplicate every N records; 0 disables duplicates",
    )

    args = parser.parse_args()

    generate_dataset(
        output_file=args.output,
        total_records=args.records,
        duplicate_every=args.duplicate_every,
    )


if __name__ == "__main__":
    main()