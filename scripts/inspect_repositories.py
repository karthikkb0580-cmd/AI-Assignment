import inspect

from ai_pipeline.database import repositories


FUNCTION_NAMES = [
    "create_startup",
    "create_product",
    "create_source_record",
    "get_startup_by_name",
]


def main():
    print("\nDATABASE REPOSITORY FUNCTIONS")
    print("=" * 65)

    for name in FUNCTION_NAMES:
        function = getattr(repositories, name, None)

        if function is None:
            print(f"\n[MISSING] {name}")
            continue

        print(f"\n[FOUND] {name}")
        print(f"Signature: {inspect.signature(function)}")


if __name__ == "__main__":
    main()