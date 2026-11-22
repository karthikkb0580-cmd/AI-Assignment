import asyncio

from sqlalchemy import inspect

from ai_pipeline.database.connection import engine


REQUIRED_TABLES = {
    "startups",
    "products",
    "research_papers",
    "jobs",
    "news",
    "source_records",
    "entity_mappings",
}


async def check_database():
    async with engine.connect() as connection:
        tables = await connection.run_sync(
            lambda sync_connection: inspect(
                sync_connection
            ).get_table_names()
        )

    existing_tables = set(tables)

    print("\nDATABASE VERIFICATION")
    print("=" * 40)

    for table in sorted(REQUIRED_TABLES):
        if table in existing_tables:
            print(f"[OK] {table}")
        else:
            print(f"[MISSING] {table}")

    missing = REQUIRED_TABLES - existing_tables

    print("=" * 40)

    if missing:
        print("Database verification FAILED")
        raise SystemExit(1)

    print("Database verification PASSED")


if __name__ == "__main__":
    asyncio.run(check_database())