import asyncio
import os
from pathlib import Path

import gspread
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.engine import make_url


ROOT = Path(__file__).resolve().parents[1]

load_dotenv(ROOT / ".env")

SHEET_ID = os.environ["GOOGLE_SHEET_ID"]


database_url = make_url(os.environ["DATABASE_URL"])

DATABASE_URL = database_url.set(
    host="127.0.0.1",
    port=5433
).render_as_string(hide_password=False)

CLIENT_SECRET = ROOT / "secrets" / "oauth-client.json"

TOKEN_FILE = ROOT / "secrets" / "authorized-user.json"


def get_google_client():
    return gspread.oauth(
        credentials_filename=str(CLIENT_SECRET),
        authorized_user_filename=str(TOKEN_FILE),
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets"
        ],
    )


async def fetch_data():

    engine = create_async_engine(DATABASE_URL)

    try:
        async with engine.connect() as conn:

            startups = (
                await conn.execute(
                    text("""
                        SELECT id, name
                        FROM startups
                        ORDER BY id
                        LIMIT 1000
                    """)
                )
            ).mappings().all()

            extractions = (
                await conn.execute(
                    text("""
                        SELECT
                            id,
                            extractor_version,
                            status
                        FROM extraction_results
                        ORDER BY id
                        LIMIT 1000
                    """)
                )
            ).mappings().all()

            jobs = (
                await conn.execute(
                    text("""
                        SELECT id, status
                        FROM resolution_jobs
                        ORDER BY id
                        LIMIT 1000
                    """)
                )
            ).mappings().all()

            counts = {}

            for table in [
                "source_records",
                "extraction_results",
                "resolution_jobs",
                "entity_mappings",
                "startups",
            ]:
                result = await conn.execute(
                    text(f"SELECT COUNT(*) FROM {table}")
                )
                counts[table] = result.scalar_one()

            return {
                "startups": startups,
                "extractions": extractions,
                "jobs": jobs,
                "counts": counts,
            }

    finally:
        await engine.dispose()


def update_worksheet(spreadsheet, title, headers, rows):

    try:
        worksheet = spreadsheet.worksheet(title)

    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(
            title=title,
            rows=max(len(rows) + 1, 100),
            cols=len(headers),
        )

    values = [headers]

    for row in rows:
        values.append([str(value) for value in row])

    worksheet.clear()

    worksheet.update(
        range_name="A1",
        values=values,
        value_input_option="RAW",
    )

    print(f"Updated {title}: {len(rows)} records")


def sync_to_sheets(data):

    client = get_google_client()

    spreadsheet = client.open_by_key(SHEET_ID)

    update_worksheet(
        spreadsheet,
        "Startups",
        ["ID", "Startup Name"],
        [
            [row["id"], row["name"]]
            for row in data["startups"]
        ],
    )

    update_worksheet(
        spreadsheet,
        "Extractions",
        ["ID", "Extractor Version", "Status"],
        [
            [
                row["id"],
                row["extractor_version"],
                row["status"],
            ]
            for row in data["extractions"]
        ],
    )

    update_worksheet(
        spreadsheet,
        "Resolution Jobs",
        ["ID", "Status"],
        [
            [row["id"], row["status"]]
            for row in data["jobs"]
        ],
    )

    update_worksheet(
        spreadsheet,
        "Pipeline Metrics",
        ["Metric", "Count"],
        [
            [name, count]
            for name, count in data["counts"].items()
        ],
    )

    print("\nGoogle Sheets synchronization completed!")


async def main():

    print("Fetching PostgreSQL data...")

    data = await fetch_data()

    print("Connecting to Google Sheets...")

    await asyncio.to_thread(sync_to_sheets, data)


if __name__ == "__main__":
    asyncio.run(main())