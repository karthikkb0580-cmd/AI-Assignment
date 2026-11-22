import argparse
import time

from ai_pipeline.services.resolution_worker import get_startup_name


def main(count):
    print("\nPIPELINE PARSING LOAD TEST")
    print("=" * 50)

    started = time.perf_counter()

    successful = 0

    for index in range(count):
        data = {
            "mock": False,
            "results": [
                {
                    "entity_type": "startup",
                    "startup": {
                        "name": f"Benchmark Startup {index}",
                    },
                }
            ],
        }

        if get_startup_name(data):
            successful += 1

    elapsed = time.perf_counter() - started

    throughput = (
        successful / elapsed
        if elapsed > 0
        else 0
    )

    print(f"Records tested: {count:,}")
    print(f"Successfully parsed: {successful:,}")
    print(f"Duration: {elapsed:.4f} seconds")
    print(f"Throughput: {throughput:,.2f} records/sec")

    assert successful == count

    print("\nPASS: Parsing load test completed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--count",
        type=int,
        default=100000,
    )

    args = parser.parse_args()

    if args.count < 1:
        parser.error("--count must be positive")

    main(args.count)
